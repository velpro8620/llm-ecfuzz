import json
import os
import re
from typing import Dict, List, Any, Union, Optional

# 使用 langchain_core 避免版本报错
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

class GenerateAgent(ChatOpenAI):
    """
    负责根据依赖关系生成种子的 Agent。
    集成 RAG 功能：如果提供了 vector_store，会先检索参数说明再生成。
    """

    # [关键修复] 显式声明 vector_store 字段，让 Pydantic 允许它的存在
    # exclude=True 表示导出模型时忽略此字段，避免序列化错误
    vector_store: Any = None

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        vector_store=None,  # 接收向量库实例
        temperature: float = 0.1,
        max_tokens: int = 4096,
        request_timeout: int = 60,
    ):
        # 1. 先调用父类初始化
        super().__init__(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )
        # 2. 再给自己的字段赋值
        self.vector_store = vector_store

    # [修复策略 1] 默认 num_seeds 从 10 降为 3，防止 Token 溢出导致 JSON 截断
    def generate_seeds(self, dependencies: Union[Dict[str, Any], List[Dict[str, Any]]], num_seeds: int = 1) -> dict:
        """
        根据依赖关系生成种子，支持 RAG 检索增强。
        """
        # ----------------- RAG 检索逻辑 -----------------
        rag_context = ""
        if self.vector_store:
            try:
                # 提取依赖中涉及的所有参数名
                query_terms = set()
                deps_list = dependencies.get("dependencies", []) if isinstance(dependencies, dict) else dependencies

                for dep in deps_list:
                    if isinstance(dep, dict):
                        if "source" in dep: query_terms.add(str(dep["source"]))
                        if "target" in dep: query_terms.add(str(dep["target"]))

                search_query = " ".join(list(query_terms))

                if search_query:
                    # 检索最相关的 5 条配置说明
                    docs = self.vector_store.similarity_search(search_query, k=5)
                    rag_context = "\n".join([f"- {doc.page_content}" for doc in docs])
            except Exception as e:
                print(f"[WARN] RAG 检索失败，将跳过: {e}")
        # ------------------------------------------------

        messages = self._build_messages(dependencies, num_seeds, rag_context)

        try:
            response = self.invoke(messages)
            content = response.content
            
            # 提取 JSON
            json_str = self._extract_json_block(content)

            # [修复策略 3] 尝试解析，如果失败尝试简单修复
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试自动闭合截断的 JSON
                fixed_json = self._try_fix_truncated_json(json_str)
                return json.loads(fixed_json)
                
        except Exception as e:
            print(f"[Error] 生成种子解析失败: {e}")
            # 打印部分内容用于调试
            debug_content = response.content if 'response' in locals() else 'None'
            print(f"[Debug] LLM 原始返回 (前500字): {debug_content[:500]}")
            # 返回空种子防止程序崩溃
            return {"seeds": []}

    def _extract_json_block(self, text: str) -> str:
        """从 LLM 返回的文本中提取 JSON 代码块"""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match: return match.group(1)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match: return match.group(0)
        # 如果找不到大括号，尝试从头开始找直到最后
        match_start = re.search(r"\{", text)
        if match_start: return text[match_start.start():]
        return text

    def _try_fix_truncated_json(self, json_str: str) -> str:
        """
        [新功能] 尝试修复因为 max_tokens 限制被截断的 JSON
        """
        print("[Warn] 检测到 JSON 解析失败，尝试自动修复截断...")
        json_str = json_str.strip()
        # 如果结尾不是 }]，尝试补全
        if not json_str.endswith("]}"):
            # 去掉最后可能不完整的字符
            # 简单的启发式修复：一直回退直到找到合法的结尾，然后闭合
            # 这里使用最粗暴但有效的方法：补全结构
            if json_str.rfind("}") > json_str.rfind("]"):
                 return json_str + "]}"
            else:
                 return json_str + "}]}"
        return json_str

    @staticmethod
    def _build_messages(dependencies, num_seeds, rag_context=""):
        dep_str = json.dumps(dependencies, indent=2, ensure_ascii=False)

        system_prompt = (
            "你是一个模糊测试种子生成专家。你的任务是根据给定的配置依赖关系，生成合法的测试种子（JSON格式）。\n\n"
            "【参考资料 (RAG)】\n"
            "以下是从官方文档中检索到的参数说明、默认值和约束信息。请严格参考：\n"
            f"```\n{rag_context}\n```\n\n"
            "【生成规则】\n"
            f"1. 请生成 {num_seeds} 个不同的种子。\n"
            "2. 每个种子必须包含依赖关系中涉及的所有参数（source 和 target）。\n"
            "3. [重要] 参数值中的双引号必须转义（例如 \"value\"）。\n"
            "4. [重要] 确保 JSON 格式严格正确，列表项之间必须有逗号。\n"
            "5. 输出必须是纯 JSON 格式，不要包含任何解释性文字。\n\n"
            "【JSON 输出格式】\n"
            "{\n"
            "  \"seeds\": [\n"
            "    {\n"
            "      \"parameters\": [\n"
            "        {\"name\": \"参数名1\", \"value\": \"参数值1\"},\n"
            "        {\"name\": \"参数名2\", \"value\": \"参数值2\"}\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = f"请根据以下依赖关系生成种子：\n{dep_str}"

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
