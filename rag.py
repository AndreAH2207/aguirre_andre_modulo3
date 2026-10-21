"""Retriever semantico pequeno.

Reutiliza el patron de chunking, embeddings y recuperacion de los Modulos 1 y 2
como UNA CAPACIDAD del agente, no como el tema central.
"""

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

from model_factory import build_embedding_client

DOCS_DIR=Path(__file__).parent/"docs"
CACHE_PATH=Path(__file__).parent/".cache"/"policy_index.json"


@dataclass(frozen=True)
class Chunk:
    source:str
    section:str
    text:str


def _chunks()->list[Chunk]:
    result=[]
    for path in sorted(DOCS_DIR.glob("*.md")):
        raw=path.read_text(encoding="utf-8")
        parts=[p.strip() for p in raw.split("\n## ") if p.strip()]
        for i,part in enumerate(parts):
            text=part if i==0 else "## "+part
            section=text.splitlines()[0].lstrip("# ").strip()
            result.append(Chunk(path.name,section,text))
    return result


def _fingerprint(chunks:list[Chunk])->str:
    raw="\n".join(f"{c.source}|{c.section}|{c.text}" for c in chunks)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cosine(a:list[float],b:list[float])->float:
    dot=sum(x*y for x,y in zip(a,b))
    na=math.sqrt(sum(x*x for x in a))
    nb=math.sqrt(sum(y*y for y in b))
    return 0.0 if na==0 or nb==0 else dot/(na*nb)


def _embed(texts:list[str])->list[list[float]]:
    model=os.getenv("OPENAI_EMBEDDING_MODEL","text-embedding-3-small")
    response=build_embedding_client().embeddings.create(model=model,input=texts)
    return [item.embedding for item in response.data]


def _load_or_build()->tuple[list[Chunk],list[list[float]]]:
    chunks=_chunks()
    fp=_fingerprint(chunks)
    model=os.getenv("OPENAI_EMBEDDING_MODEL","text-embedding-3-small")

    if CACHE_PATH.exists():
        cached=json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if cached.get("fingerprint")==fp and cached.get("model")==model:
            return chunks,cached["vectors"]

    vectors=_embed([c.text for c in chunks])
    CACHE_PATH.parent.mkdir(parents=True,exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps({"fingerprint":fp,"model":model,"vectors":vectors}),
        encoding="utf-8",
    )
    return chunks,vectors


def search(query:str,top_k:int=3)->list[dict]:
    chunks,vectors=_load_or_build()
    query_vector=_embed([query])[0]
    scored=[(_cosine(query_vector,v),i) for i,v in enumerate(vectors)]
    scored.sort(reverse=True)

    results=[]
    for score,i in scored[:max(1,min(top_k,5))]:
        chunk=chunks[i]
        results.append({
            "source":chunk.source,
            "section":chunk.section,
            "score":round(score,4),
            "content":chunk.text,
            "source_ref":f"[RAG:{chunk.source}#{chunk.section}]",
        })
    return results
