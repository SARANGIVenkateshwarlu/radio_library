"""LangGraph pipeline builder."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import RadioState


def build_graph():
    g = StateGraph(RadioState)
    g.add_node("load_audio", nodes.load_audio)
    g.add_node("transcribe", nodes.transcribe)
    g.add_node("correct", nodes.correct)
    g.add_node("jyutping", nodes.jyutping)
    g.add_node("translate", nodes.translate)
    g.add_node("segment_blocks", nodes.segment_blocks)
    g.add_node("generate_pdf", nodes.generate_pdf)
    g.add_node("save_to_library", nodes.save_to_library)

    g.add_edge(START, "load_audio")
    g.add_edge("load_audio", "transcribe")
    g.add_edge("transcribe", "correct")
    g.add_edge("correct", "jyutping")
    g.add_edge("jyutping", "translate")
    g.add_edge("translate", "segment_blocks")
    g.add_edge("segment_blocks", "generate_pdf")
    g.add_edge("generate_pdf", "save_to_library")
    g.add_edge("save_to_library", END)
    return g.compile()


def run(audio_path: str, mock_asr: bool = True) -> RadioState:
    app = build_graph()
    return app.invoke({"audio_path": audio_path, "mock_asr": mock_asr})
