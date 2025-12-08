import json
from typing import List, Dict, Any
from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

try:
    from fuzzer.RAG import get_vectorstore
except ImportError:
    try:
        from RAG import get_vectorstore
    except ImportError:
        import sys, os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from fuzzer.RAG import get_vectorstore

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

class GenerateAgent:
    """
    种子生成 Agent (使用组合模式)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: int = 32768,
        request_timeout: int = 60,
        use_rag: bool = True
    ):
        # 1. 初始化内部 LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )
        
        # 2. 设置自身属性
        self.use_rag = use_rag
        self.vectorstore = None
        
        if self.use_rag:
            try:
                self.vectorstore = get_vectorstore()
                if self.vectorstore:
                    print("[GenerateAgent] ✅ RAG 向量库连接成功")
                else:
                    self.use_rag = False
            except Exception as e:
                print(f"[GenerateAgent] ⚠️ RAG 初始化失败: {e}")
                self.use_rag = False

    def _retrieve_param_details(self, dependencies: Dict[str, Any]) -> str:
        if not self.use_rag or not self.vectorstore:
            return ""

        param_names = set()
        deps = dependencies.get("dependencies", [])
        for d in deps:
            if "source" in d: param_names.add(d["source"])
            if "target" in d: param_names.add(d["target"])
        
        if not param_names:
            return ""

        print(f"[GenerateAgent] 正在检索 {len(param_names)} 个参数的定义...")
        context_list = []
        
        for param in list(param_names)[:15]:
            try:
                # 尝试精确匹配
                results = self.vectorstore.similarity_search(
                    f"配置项: {param}", 
                    k=1, 
                    filter={"name": param}
                )
                if not results:
                    results = self.vectorstore.similarity_search(param, k=1)
                
                if results:
                    doc = results[0]
                    context_list.append(f"【{param}】定义:\n{doc.page_content}")
            except Exception:
                continue
                
        return "\n\n".join(context_list)

    def generate_seeds(self, dependencies: Dict[str, Any], num_seeds: int = 10) -> dict:
        param_context = self._retrieve_param_details(dependencies)
        deps_json = json.dumps(dependencies, ensure_ascii=False, indent=2)
        
        system_msg = SystemMessage(
            content="你是一个模糊测试种子生成专家。请根据依赖关系和参数定义生成高质量测试配置。"
        )
        
        context_str = ""
        if param_context:
            context_str = (
                "\n\n【参数详细定义 (RAG)】\n"
                f"{param_context}\n"
                "请严格参考上述定义（数据类型、取值范围、默认值）来生成合法的参数值。\n"
            )

        human_msg = HumanMessage(
            content=(
                "【依赖关系】\n"
                f"```json\n{deps_json}\n```\n"
                f"{context_str}"
                f"\n请生成 {num_seeds} 个测试种子 (JSON格式)。\n"
                "格式：{ \"seeds\": [ { \"parameters\": [{\"name\": \"...\", \"value\": \"...\"}], \"reason\": \"...\" } ] }"
            )
        )

        # 修改点：调用 self.llm.invoke
        response = self.llm.invoke([system_msg, human_msg])
        return json.loads(clean_json_text(response.content))
