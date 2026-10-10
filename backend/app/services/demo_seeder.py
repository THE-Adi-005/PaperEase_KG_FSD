"""Demo Seeder — pre-populates Neo4j with 3 realistic papers, figures, tables, and a KG."""

import logging
from app.models.schemas import ParsedPaper, Author, Section, Triple, PaperStatus, FigureData, TableData
from app.services.neo4j_client import neo4j_service
import asyncio

logger = logging.getLogger(__name__)

async def seed_demo_data():
    """Populate Neo4j with 3 seminal AI papers, tables, figures, and their Knowledge Graph."""
    logger.info("Starting demo KG seeding...")

    # --- 1. Attention Is All You Need (Transformer) ---
    paper1 = ParsedPaper(
        id="demo_attention_2017",
        title="Attention Is All You Need",
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose the Transformer, a model architecture eschewing recurrence and entirely relying on an attention mechanism.",
        authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer"), Author(name="Niki Parmar")],
        sections=[
            Section(id="sec_att_1", title="Introduction", text="Recurrent neural networks, long short-term memory and gated recurrent neural networks have been firmly established as state of the art approaches in sequence modeling. Attention mechanisms allow modeling of dependencies regardless of distance.", order=1),
            Section(id="sec_att_2", title="Model Architecture", text="Most competitive neural sequence transduction models have an encoder-decoder structure. The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder.", order=2),
            Section(id="sec_att_3", title="Results & Evaluation", text="On the WMT 2014 English-to-German translation task, the big transformer model achieves a new state of the art BLEU score of 28.4, outperforming existing best models by over 2 BLEU points. On English-to-French, our model establishes a state-of-the-art BLEU score of 41.8.", order=3),
        ],
        figures=[
            FigureData(
                id="fig_att_1",
                label="Figure 1: The Transformer Architecture",
                caption="The Transformer model architecture showing stacked multi-head attention and point-wise feed-forward sublayers for encoder and decoder.",
                image_path=None,
                page_number=3
            )
        ],
        tables=[
            TableData(
                id="tbl_att_1",
                label="Table 1: Translation Benchmark on WMT 2014",
                caption="Maximum BLEU score evaluation on WMT 2014 English-to-German and English-to-French translation tasks.",
                headers=["Architecture", "EN-DE BLEU", "EN-FR BLEU", "Training FLOPs", "Params"],
                rows=[
                    ["ByteNet", "23.75", "---", "---", "150M"],
                    ["Deep-Att + PosUnk", "---", "39.20", "---", "---"],
                    ["ConvS2S", "25.16", "40.46", "9.6 × 10^18", "216M"],
                    ["Transformer (Base Model)", "27.30", "38.10", "3.3 × 10^18", "65M"],
                    ["Transformer (Big Model)", "28.40", "41.80", "2.3 × 10^19", "213M"]
                ],
                page_number=8
            ),
            TableData(
                id="tbl_att_2",
                label="Table 2: Layer Complexity & Maximum Path Length",
                caption="Theoretical comparison of computational complexity and sequential operations across layer types.",
                headers=["Layer Type", "Complexity / Layer", "Sequential Ops", "Max Path Length"],
                rows=[
                    ["Self-Attention", "O(n² · d)", "O(1)", "O(1)"],
                    ["Recurrent (LSTM)", "O(n · d²)", "O(n)", "O(n)"],
                    ["Convolutional (k<n)", "O(k · n · d²)", "O(1)", "O(log_k(n))"],
                    ["Self-Attention (Restricted)", "O(r · n · d)", "O(1)", "O(n/r)"]
                ],
                page_number=6
            )
        ]
    )

    triples1 = [
        Triple(head="Transformer", head_type="Method", relation="ACHIEVES", tail="BLEU=28.4", tail_type="Metric", source_paper_id=paper1.id, source_section_id="sec_att_3"),
        Triple(head="Transformer", head_type="Method", relation="EVALUATED_ON", tail="WMT 2014 English-to-German", tail_type="Dataset", source_paper_id=paper1.id, source_section_id="sec_att_3"),
        Triple(head="Transformer", head_type="Method", relation="USES_METHOD", tail="Multi-Head Attention", tail_type="Method", source_paper_id=paper1.id, source_section_id="sec_att_2"),
        Triple(head="Self-Attention", head_type="Concept", relation="DISCUSSES_CONCEPT", tail="Parallelization", tail_type="Concept", source_paper_id=paper1.id, source_section_id="sec_att_1"),
    ]

    # --- 2. BERT ---
    paper2 = ParsedPaper(
        id="demo_bert_2018",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        abstract="We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations.",
        authors=[Author(name="Jacob Devlin"), Author(name="Ming-Wei Chang"), Author(name="Kenton Lee")],
        sections=[
            Section(id="sec_bert_1", title="Introduction", text="Language model pre-training has been shown to be effective for improving many natural language processing tasks. Pre-trained representations can either be feature-based or fine-tuning based.", order=1),
            Section(id="sec_bert_2", title="BERT Architecture", text="The BERT model architecture is a multi-layer bidirectional Transformer encoder based on the original Transformer architecture. We denote the number of layers as L, hidden size as H, and attention heads as A.", order=2),
            Section(id="sec_bert_3", title="Experiments & Benchmarks", text="On SQuAD v1.1, BERT achieves an F1 score of 93.2, outperforming the previous state-of-the-art by 1.5 points. On GLUE, BERT Large achieves an overall score of 82.1.", order=3),
        ],
        figures=[
            FigureData(
                id="fig_bert_1",
                label="Figure 1: BERT Pre-training & Fine-tuning Framework",
                caption="Overall pre-training and fine-tuning procedures for BERT showing bidirectional attention across all layers.",
                image_path=None,
                page_number=3
            )
        ],
        tables=[
            TableData(
                id="tbl_bert_1",
                label="Table 1: GLUE Benchmark Test Results",
                caption="GLUE Test results scored on the official evaluation server across 8 benchmark tasks.",
                headers=["Model", "MNLI (m/mm)", "QNLI", "QQP", "RTE", "SST-2", "GLUE Score"],
                rows=[
                    ["Pre-OpenAI SOTA", "80.6 / 80.0", "82.3", "86.0", "61.7", "90.4", "74.0"],
                    ["OpenAI GPT", "82.1 / 81.4", "87.4", "87.7", "56.0", "91.3", "75.1"],
                    ["BERT Base (110M)", "84.6 / 83.4", "90.5", "89.2", "66.4", "93.5", "79.6"],
                    ["BERT Large (340M)", "86.7 / 85.9", "92.7", "89.6", "70.1", "94.9", "82.1"]
                ],
                page_number=5
            ),
            TableData(
                id="tbl_bert_2",
                label="Table 2: SQuAD v1.1 / v2.0 Question Answering",
                caption="Stanford Question Answering Dataset results: Exact Match (EM) and F1 evaluation.",
                headers=["Model", "SQuAD v1.1 EM", "SQuAD v1.1 F1", "SQuAD v2.0 EM", "SQuAD v2.0 F1"],
                rows=[
                    ["Human Performance", "82.3", "91.2", "86.8", "89.5"],
                    ["BiDAF + ELMo", "78.6", "85.8", "63.4", "66.3"],
                    ["BERT Base", "80.8", "88.5", "73.7", "76.3"],
                    ["BERT Large", "85.1", "93.2", "78.7", "81.9"]
                ],
                page_number=6
            )
        ]
    )

    triples2 = [
        Triple(head="BERT", head_type="Method", relation="EXTENDS", tail="Transformer Encoder", tail_type="Method", source_paper_id=paper2.id, source_section_id="sec_bert_2"),
        Triple(head="BERT", head_type="Method", relation="ACHIEVES", tail="F1=93.2", tail_type="Metric", source_paper_id=paper2.id, source_section_id="sec_bert_3"),
        Triple(head="BERT", head_type="Method", relation="EVALUATED_ON", tail="SQuAD v1.1", tail_type="Dataset", source_paper_id=paper2.id, source_section_id="sec_bert_3"),
        Triple(head="BERT", head_type="Method", relation="USES_METHOD", tail="Masked Language Modeling", tail_type="Method", source_paper_id=paper2.id, source_section_id="sec_bert_2"),
    ]

    # --- 3. GPT-3 ---
    paper3 = ParsedPaper(
        id="demo_gpt3_2020",
        title="Language Models are Few-Shot Learners",
        abstract="Recent work has demonstrated substantial gains on many NLP tasks by pre-training on a large corpus of text followed by fine-tuning. Here we show that scaling up language models greatly improves task-agnostic, few-shot performance.",
        authors=[Author(name="Tom B. Brown"), Author(name="Benjamin Mann"), Author(name="Nick Ryder")],
        sections=[
            Section(id="sec_gpt3_1", title="Introduction", text="We train GPT-3, an autoregressive language model with 175 billion parameters, 10x more than any previous non-sparse language model, and test its performance in the few-shot setting.", order=1),
            Section(id="sec_gpt3_2", title="Approach & Architecture", text="We use the same model and architecture as GPT-2, including the modified initialization and pre-activation residual connections, but scale model depth and width across 8 parameter tiers.", order=2),
            Section(id="sec_gpt3_3", title="Results on SuperGLUE", text="On SuperGLUE, GPT-3 175B achieves 71.8% accuracy in the few-shot setting, demonstrating competitive results with fine-tuned models like BERT-Large without gradient updates.", order=3),
        ],
        figures=[
            FigureData(
                id="fig_gpt3_1",
                label="Figure 1: Few-Shot In-Context Learning Scaling Law",
                caption="Aggregate accuracy across benchmark NLP tasks as parameter scale increases from 125M to 175B.",
                image_path=None,
                page_number=4
            )
        ],
        tables=[
            TableData(
                id="tbl_gpt3_1",
                label="Table 1: SuperGLUE Performance across Parameter Scales",
                caption="In-context few-shot evaluation across model sizes on SuperGLUE tasks.",
                headers=["Model Tier", "BoolQ", "CB", "MultiRC", "ReCoRD", "WSC", "SuperGLUE Avg"],
                rows=[
                    ["GPT-3 Small (125M)", "60.4", "42.9", "45.1", "54.8", "59.6", "52.6"],
                    ["GPT-3 Medium (350M)", "64.1", "58.9", "51.3", "62.3", "61.5", "59.6"],
                    ["GPT-3 Large (1.3B)", "68.2", "66.7", "58.0", "70.8", "65.4", "65.8"],
                    ["GPT-3 175B (Zero-Shot)", "76.4", "75.6", "72.5", "89.0", "64.4", "67.3"],
                    ["GPT-3 175B (Few-Shot)", "77.7", "82.1", "75.4", "90.2", "75.0", "71.8"]
                ],
                page_number=14
            )
        ]
    )

    triples3 = [
        Triple(head="GPT-3", head_type="Method", relation="EXTENDS", tail="Transformer Decoder", tail_type="Method", source_paper_id=paper3.id, source_section_id="sec_gpt3_2"),
        Triple(head="GPT-3", head_type="Method", relation="ACHIEVES", tail="Accuracy=71.8%", tail_type="Metric", source_paper_id=paper3.id, source_section_id="sec_gpt3_3"),
        Triple(head="GPT-3", head_type="Method", relation="EVALUATED_ON", tail="SuperGLUE", tail_type="Dataset", source_paper_id=paper3.id, source_section_id="sec_gpt3_3"),
        Triple(head="GPT-3", head_type="Method", relation="USES_METHOD", tail="Few-Shot Learning", tail_type="Concept", source_paper_id=paper3.id, source_section_id="sec_gpt3_1"),
    ]

    # Insert papers and triples
    for paper, triples in [(paper1, triples1), (paper2, triples2), (paper3, triples3)]:
        await neo4j_service.merge_paper(paper)
        await neo4j_service.update_paper_status(paper.id, PaperStatus.COMPLETE, 100.0)
        await neo4j_service.merge_triples(triples)

    # Cross-paper SAME_AS edges (simulating the embedding link step)
    cross_paper_links = [
        ("Transformer", "Transformer Encoder", 0.90),
        ("Transformer", "Transformer Decoder", 0.85),
    ]

    async with neo4j_service.driver.session() as session:
        for a, b, sim in cross_paper_links:
            await session.run(
                """MATCH (na {name: $name_a}), (nb {name: $name_b})
                   WHERE na <> nb
                   MERGE (na)-[:SAME_AS {similarity: $sim, source_paper_id: 'demo_linker'}]->(nb)""",
                name_a=a, name_b=b, sim=sim
            )

    logger.info("Demo KG seeding complete with figures & tables!")
    return ["demo_attention_2017", "demo_bert_2018", "demo_gpt3_2020"]
