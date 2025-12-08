import json
from typing import List, Dict, Any
from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 尝试导入 RAG 模块
try:
    from fuzzer.RAG import get_vectorstore
except ImportError:
    try:
        from RAG import get_vectorstore
    except ImportError:
        import sys, os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from fuzzer.RAG import get_vectorstore

# 尝试导入 json_repair
try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]
    return text

class AnalysisAgent:
    """
    配置依赖分析 Agent (支持智能路由检索)
    """

    # 预定义向量库中已有的“标准参考书目”
    # 你可以根据实际 default_conf_file 里的内容修改这个列表
    KNOWN_FILES = [
        "core-default.xml",
        "hdfs-default.xml",
        "hbase-default.xml", 
        "zoo.cfg",
        "alluxio-site.properties"
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: int = 32768,
        request_timeout: int = 120,
        use_rag: bool = True
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )
        
        self.use_rag = use_rag
        self.vectorstore = None
        
        if self.use_rag:
            try:
                self.vectorstore = get_vectorstore()
                if self.vectorstore:
                    print("[AnalysisAgent] ✅ RAG 向量库连接成功")
                else:
                    self.use_rag = False
            except Exception as e:
                print(f"[AnalysisAgent] ⚠️ RAG 初始化失败: {e}")
                self.use_rag = False

    def _determine_scope(self, content_snippet: str) -> List[str]:
        """
        [智能路由]：根据输入文件片段，判断需要检索哪些相关文件。
        """
        system_msg = SystemMessage(content=(
            "你是一个大数据组件专家。请根据用户提供的配置文件片段，判断该文件属于哪个组件（如 HDFS, HBase, ZooKeeper 等），"
            "并推断分析该配置可能需要参考哪些上游依赖文件。\n"
            f"可选的文件列表为：{json.dumps(self.KNOWN_FILES)}\n"
            "请返回一个 JSON 对象，格式为：{\"relevant_files\": [\"file1\", \"file2\"]}\n"
            "注意：必须包含文件自身（如果它在列表里），以及它直接依赖的组件（例如 HBase 依赖 HDFS 和 ZooKeeper）。"
        ))
        
        human_msg = HumanMessage(content=f"配置文件片段：\n{content_snippet}")
        
        try:
            # 使用 LLM 快速判断
            response = self.llm.invoke([system_msg, human_msg])
            result = json.loads(clean_json_text(response.content))
            files = result.get("relevant_files", [])
            # 过滤掉不在我们列表里的幻觉文件
            valid_files = [f for f in files if f in self.KNOWN_FILES]
            return valid_files
        except Exception as e:
            print(f"[AnalysisAgent] ⚠️ 路由分析失败: {e}，将回退到全库检索")
            return [] # 返回空列表表示不进行过滤（全库检索）

    def _retrieve_context(self, content_input: str) -> str:
        if not self.use_rag or not self.vectorstore:
            return ""
        
        # 1. 截取前 1000 字符用于路由判断（足够识别是哪个组件了）
        snippet = content_input[:1000]
        
        # 2. [新增] 智能路由：决定要查哪些文件
        print("[AnalysisAgent] 🤖 正在分析文件类型及依赖范围...")
        target_files = self._determine_scope(snippet)
        
        search_kwargs = {"k": 5}
        
        # 3. [新增] 构造过滤器
        if target_files:
            print(f"[AnalysisAgent] 🎯 锁定检索范围: {target_files}")
            # ChromaDB 的 $in 语法： {"filename": {"$in": [...]}}
            search_kwargs["filter"] = {"filename": {"$in": target_files}}
        else:
            print("[AnalysisAgent] 🌐 未识别特定范围，执行全库检索")

        # 4. 执行检索
        query = content_input[:300].replace("\n", " ") # 用前300字做语义查询
        try:
            results = self.vectorstore.similarity_search(query, **search_kwargs)
            
            if not results:
                print("[AnalysisAgent] ⚠️ 未检索到相关内容")
                return ""

            context = "\n".join([f"---参考配置 ({doc.metadata.get('filename')})---\n{doc.page_content}" for doc in results])
            return context
        except Exception as e:
            print(f"[AnalysisAgent] 检索执行出错: {e}")
            return ""

    @staticmethod
    def _build_messages(config_content: str, rag_context: str = "") -> List:
        system_msg = SystemMessage(
            content=(
                "你是一个配置参数分析专家。请分析配置参数之间的以下依赖关系类型：\n"
                "1. 控制依赖 (Control Dependency)\n"
                "2. 值关系依赖 (Value Dependency)\n"
                "3. 默认值依赖 (Default Value Dependency)\n"
                "4. 行为依赖 (Behavioral Dependency)\n"
                "输出必须是一个合法的 JSON 对象，不要包含任何 Markdown 标记或额外文本。"
            )
        )

        context_prompt = ""
        if rag_context:
            context_prompt = (
                f"\n\n【参考知识库 (已过滤相关组件)】\n"
                f"{rag_context}\n"
                f"--------------------------------\n"
                f"请结合上述参考资料（特别是跨组件的参数引用）进行分析。\n"
            )

        # 截断保护
        if len(config_content) > 100000:
            print(f"[AnalysisAgent] ⚠️ 配置内容过长 ({len(config_content)} chars)，已截取前 100000 字符...")
            config_content = config_content[:100000] + "\n... (truncated)"

        human_msg = HumanMessage(
            content=(
                f"{context_prompt}"
                "请分析以下配置内容的参数依赖关系：\n"
                "```xml\n"
                f"{config_content}\n"
                "```\n"
                "返回格式示例：\n"
                "{\n"
                '  "dependencies": [\n'
                "    {\n"
                '      "source": "源参数", "target": "目标参数", "type": "依赖类型", "relationship": "描述"\n'
                "    }\n"
                "  ]\n"
                "}\n"
            )
        )
        return [system_msg, human_msg]

    def analyze_config_dependencies(self, config_content: str) -> dict:
        # 1. 路由 + 检索
        rag_context = self._retrieve_context(config_content)
        
        # 2. 构造分析 Prompt
        messages = self._build_messages(config_content, rag_context)
        
        print("[AnalysisAgent] 🧠 正在进行深度依赖分析...")
        response = self.llm.invoke(messages)
        
        cleaned_text = clean_json_text(response.content)
        
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            print(f"\n[AnalysisAgent] ❌ JSON 解析失败: {e}")
            if HAS_JSON_REPAIR:
                print("[AnalysisAgent] 🔄 尝试自动修复 JSON...")
                try:
                    return json_repair.loads(cleaned_text)
                except Exception:
                    return {"dependencies": []}
            else:
                return {"dependencies": []}
