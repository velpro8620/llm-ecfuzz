try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import xml.etree.ElementTree as ET
import torch
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ================= 配置部分 =================
# 向量数据库保存路径 (确保与其他文件引用一致)
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "../chroma_db_data")
# 配置文件所在目录
CONF_DIR = os.path.join(os.path.dirname(__file__), "../data/default_conf_file")

# ================= 加载器定义 =================
class MultiConfigLoader(BaseLoader):
    """
    通用配置加载器，支持加载文件夹下所有的 .xml, .cfg, .properties 文件
    """
    def __init__(self, dir_path: str):
        self.dir_path = dir_path

    def load(self):
        docs = []
        if not os.path.exists(self.dir_path):
            print(f"❌ 目录不存在: {self.dir_path}")
            return docs

        print(f"📂 正在扫描目录: {self.dir_path} ...")
        
        for filename in os.listdir(self.dir_path):
            file_path = os.path.join(self.dir_path, filename)
            if os.path.isdir(file_path):
                continue

            try:
                if filename.endswith(".xml"):
                    docs.extend(self._parse_xml(file_path, filename))
                elif filename.endswith((".cfg", ".properties")):
                    docs.extend(self._parse_properties(file_path, filename))
            except Exception as e:
                print(f"⚠️ 解析文件 {filename} 时出错: {e}")

        return docs

    def _parse_xml(self, file_path, filename):
        xml_docs = []
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for prop in root.findall('property'):
            name_node = prop.find('name')
            value_node = prop.find('value')
            desc_node = prop.find('description')
            
            name = name_node.text.strip() if (name_node is not None and name_node.text) else "unknown"
            value = value_node.text.strip() if (value_node is not None and value_node.text) else ""
            
            description = ""
            if desc_node is not None and desc_node.text:
                description = " ".join(desc_node.text.split())

            page_content = f"配置项: {name}\n默认值: {value}\n说明: {description}"
            
            xml_docs.append(Document(
                page_content=page_content,
                metadata={
                    "source": file_path,
                    "filename": filename,
                    "name": name,
                    "type": "xml_config"
                }
            ))
        return xml_docs

    def _parse_properties(self, file_path, filename):
        prop_docs = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_comments = []
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("#") or line.startswith("!"):
                current_comments.append(line.lstrip("#! ").strip())
                continue
            
            if "=" in line:
                parts = line.split("=", 1)
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
                description = " ".join(current_comments)
                
                page_content = f"配置项: {key}\n当前值: {value}\n说明: {description}"
                
                prop_docs.append(Document(
                    page_content=page_content,
                    metadata={
                        "source": file_path,
                        "filename": filename,
                        "name": key,
                        "type": "properties_config"
                    }
                ))
                current_comments = []
        return prop_docs

# ================= 核心接口：获取向量库实例 =================
def get_vectorstore():
    """
    初始化并返回向量数据库实例 (供 Agent 调用)
    """
    # 自动检测设备
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 初始化 Embedding
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3", 
        model_kwargs={'device': device}, 
        encode_kwargs={'normalize_embeddings': True}
    )

    # 加载向量库
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        return Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings,
            collection_name="hdfs_config_bge_m3"
        )
    else:
        # 如果库不存在，返回 None 或抛出异常，由调用方处理
        print(f"⚠️ 警告: 向量库不存在于 {PERSIST_DIR}，RAG 功能将不可用。请先运行 RAG.py 初始化。")
        return None

# ================= 主初始化逻辑 (建库使用) =================
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 正在使用计算设备: {device}")

    print("⏳ 正在加载模型...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3", 
        model_kwargs={'device': device}, 
        encode_kwargs={'normalize_embeddings': True}
    )

    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print(f"🔄 检测到本地数据库 {PERSIST_DIR}，跳过重建。")
        # 如果想强制重建，请手动删除文件夹
    else:
        print("🆕 本地无数据，开始加载配置文件...")
        loader = MultiConfigLoader(CONF_DIR)
        all_documents = loader.load()

        if all_documents:
            print(f"📥 正在存入 {len(all_documents)} 条数据...")
            Chroma.from_documents(
                documents=all_documents, 
                embedding=embeddings,
                collection_name="hdfs_config_bge_m3",
                persist_directory=PERSIST_DIR
            )
            print("✅ 入库成功！")
        else:
            print("⚠️ 未找到配置文件，请检查路径。")
