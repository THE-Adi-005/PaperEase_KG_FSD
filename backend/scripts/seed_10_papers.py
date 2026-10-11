import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import logging
from app.models.schemas import ParsedPaper, Author, Section, Triple, PaperStatus, FigureData, TableData
from app.services.neo4j_client import neo4j_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_10_papers")

async def run():
    await neo4j_service.connect()
    
    # 1. Clean phantom / unnamed paper nodes
    async with neo4j_service.driver.session() as session:
        result = await session.run(
            """MATCH (p:Paper)
               WHERE p.id IS NULL OR p.id = '' OR p.title IS NULL OR p.title = ''
               DETACH DELETE p"""
        )
        logger.info("Cleaned phantom paper nodes.")

    # 2. Add RoBERTa (2019)
    roberta = ParsedPaper(
        id="demo_roberta_2019",
        title="RoBERTa: A Robustly Optimized BERT Pretraining Approach",
        abstract="Language model pretraining has led to significant performance gains, but careful hyperparameter tuning is critical. We present a replication study of BERT pretraining that carefully measures the impact of key hyperparameters and training data size. We find that BERT was significantly undertrained and can match or exceed every post-BERT model.",
        authors=[Author(name="Yinhan Liu"), Author(name="Myle Ott"), Author(name="Naman Goyal")],
        sections=[
            Section(id="sec_rob_1", title="Introduction", text="We carefully evaluate hyperparameter choices in BERT pretraining, finding that dynamic masking, removing the next sentence prediction loss, training on longer sequences, and larger batch sizes yields substantial improvements.", order=1),
            Section(id="sec_rob_2", title="Pretraining Methodology", text="RoBERTa modifies BERT by training with dynamic masking, full-sentences without NSP loss, large mini-batches of 8K sequences, and a larger byte-level BPE vocabulary of 50K subwords.", order=2),
            Section(id="sec_rob_3", title="Benchmark Results on GLUE & SQuAD", text="On GLUE, RoBERTa Large establishes a new state of the art with an 88.5 score, outperforming BERT Large (82.1) and XLNet (88.4). On SQuAD v2.0, RoBERTa achieves 89.8 F1.", order=3),
        ],
        figures=[
            FigureData(
                id="fig_rob_1",
                label="Figure 1: RoBERTa Dynamic Masking vs Static Masking",
                caption="Dynamic masking generates a new masking pattern each time a sequence is fed to the model, improving robustness over static BERT masking.",
                image_path=None,
                page_number=4
            )
        ],
        tables=[
            TableData(
                id="tbl_rob_1",
                label="Table 1: GLUE Benchmark Comparison Across SOTA Models",
                caption="Comparison of RoBERTa against BERT and XLNet across GLUE tasks.",
                headers=["Model", "MNLI", "QNLI", "QQP", "RTE", "SST-2", "GLUE Score"],
                rows=[
                    ["BERT Large", "86.7", "92.7", "89.6", "70.1", "94.9", "82.1"],
                    ["XLNet Large", "90.2", "94.7", "90.3", "86.3", "95.6", "88.4"],
                    ["RoBERTa Large", "90.8", "95.4", "92.2", "88.2", "96.7", "88.5"],
                ],
                page_number=6
            )
        ]
    )

    triples_roberta = [
        Triple(head="RoBERTa", head_type="Method", relation="EXTENDS", tail="BERT", tail_type="Method", source_paper_id=roberta.id, source_section_id="sec_rob_1"),
        Triple(head="RoBERTa", head_type="Method", relation="ACHIEVES", tail="GLUE=88.5", tail_type="Metric", source_paper_id=roberta.id, source_section_id="sec_rob_3"),
        Triple(head="RoBERTa", head_type="Method", relation="EVALUATED_ON", tail="GLUE", tail_type="Dataset", source_paper_id=roberta.id, source_section_id="sec_rob_3"),
        Triple(head="RoBERTa", head_type="Method", relation="USES_METHOD", tail="Dynamic Masking", tail_type="Method", source_paper_id=roberta.id, source_section_id="sec_rob_2"),
    ]

    # 3. Add T5 (2020)
    t5 = ParsedPaper(
        id="demo_t5_2020",
        title="Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer",
        abstract="Transfer learning has emerged as a powerful technique in natural language processing. In this paper, we explore the landscape of transfer learning by introducing a unified framework that converts every language problem into a text-to-text format. Our systematic study evaluates model architectures, pretraining objectives, unlabeled datasets, transfer approaches, and scale.",
        authors=[Author(name="Colin Raffel"), Author(name="Noam Shazeer"), Author(name="Adam Roberts")],
        sections=[
            Section(id="sec_t5_1", title="Introduction", text="With T5, we propose reframing all NLP tasks into a unified text-to-text format where input and output are always text strings. This enables applying the exact same model, objective, training procedure, and decoding process across diverse tasks.", order=1),
            Section(id="sec_t5_2", title="Colossal Clean Crawled Corpus (C4)", text="We introduce the C4 dataset, a cleaned version of Common Crawl containing over 750GB of English text, which provides high-quality pretraining data.", order=2),
            Section(id="sec_t5_3", title="Empirical Evaluation & Results", text="Our 11-billion parameter T5 model achieves state-of-the-art results on 24 tasks including GLUE (89.7), SuperGLUE (89.3), SQuAD (94.1 F1), and CNN/Daily Mail summarization (43.5 ROUGE-2).", order=3),
        ],
        figures=[
            FigureData(
                id="fig_t5_1",
                label="Figure 1: The Unified Text-to-Text Framework",
                caption="Every task including translation, question answering, classification, and summarization is formulated as generating target text given input prompt text.",
                image_path=None,
                page_number=2
            )
        ],
        tables=[
            TableData(
                id="tbl_t5_1",
                label="Table 1: Benchmark Results Across Unified NLP Benchmarks",
                caption="Performance comparison across GLUE, SuperGLUE, SQuAD, and Summarization.",
                headers=["Model", "GLUE", "SuperGLUE", "SQuAD F1", "CNN/DM ROUGE-2", "Parameters"],
                rows=[
                    ["BERT Large", "82.1", "---", "93.2", "---", "340M"],
                    ["RoBERTa Large", "88.5", "---", "94.6", "---", "355M"],
                    ["T5-Base", "82.7", "75.1", "90.8", "21.3", "220M"],
                    ["T5-11B", "89.7", "89.3", "94.1", "43.5", "11B"],
                ],
                page_number=8
            )
        ]
    )

    triples_t5 = [
        Triple(head="T5", head_type="Method", relation="EXTENDS", tail="Transformer", tail_type="Method", source_paper_id=t5.id, source_section_id="sec_t5_1"),
        Triple(head="T5", head_type="Method", relation="ACHIEVES", tail="SuperGLUE=89.3", tail_type="Metric", source_paper_id=t5.id, source_section_id="sec_t5_3"),
        Triple(head="T5", head_type="Method", relation="TRAINED_ON", tail="C4 Dataset", tail_type="Dataset", source_paper_id=t5.id, source_section_id="sec_t5_2"),
        Triple(head="T5", head_type="Method", relation="USES_METHOD", tail="Text-to-Text Formulation", tail_type="Concept", source_paper_id=t5.id, source_section_id="sec_t5_1"),
    ]

    # 4. Add ELECTRA (2020)
    electra = ParsedPaper(
        id="demo_electra_2020",
        title="ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators",
        abstract="Masked language modeling pre-training methods such as BERT corrupt the input by replacing some tokens with [MASK] and then train a model to reconstruct the original tokens. We propose replaced token detection, a pre-training task where the model learns to distinguish real input tokens from plausible synthetic tokens generated by a small generator network.",
        authors=[Author(name="Kevin Clark"), Author(name="Minh-Thang Luong"), Author(name="Quoc V. Le")],
        sections=[
            Section(id="sec_elec_1", title="Introduction", text="Instead of predicting 15% masked tokens like BERT, ELECTRA trains a discriminator network over all tokens in the sequence, achieving dramatically higher sample efficiency.", order=1),
            Section(id="sec_elec_2", title="Replaced Token Detection Objective", text="A small generator model predicts masked tokens, and the discriminator predicts binary labels indicating whether each token is original or replaced.", order=2),
            Section(id="sec_elec_3", title="GLUE & SQuAD Evaluation", text="ELECTRA-Small outperforms GPT with only 14M parameters. ELECTRA-Large achieves an 89.5 GLUE score, matching RoBERTa while requiring less than 25% of the compute.", order=3),
        ],
        figures=[
            FigureData(
                id="fig_elec_1",
                label="Figure 1: Generator-Discriminator Pre-training Architecture",
                caption="Overview of Replaced Token Detection: the generator replaces masked tokens, while the discriminator predicts whether each token was replaced.",
                image_path=None,
                page_number=3
            )
        ],
        tables=[
            TableData(
                id="tbl_elec_1",
                label="Table 1: GLUE Score vs Pretraining Compute Flops",
                caption="Comparison of compute efficiency and GLUE scores between BERT, RoBERTa, XLNet, and ELECTRA.",
                headers=["Model", "GLUE Score", "Compute Multiplier", "Params"],
                rows=[
                    ["BERT Base", "79.6", "1.0×", "110M"],
                    ["RoBERTa Base", "86.4", "10.0×", "125M"],
                    ["ELECTRA Base", "85.1", "1.0×", "110M"],
                    ["ELECTRA Large", "89.5", "4.0×", "335M"],
                ],
                page_number=7
            )
        ]
    )

    triples_electra = [
        Triple(head="ELECTRA", head_type="Method", relation="EXTENDS", tail="Transformer Encoder", tail_type="Method", source_paper_id=electra.id, source_section_id="sec_elec_1"),
        Triple(head="ELECTRA", head_type="Method", relation="ACHIEVES", tail="GLUE=89.5", tail_type="Metric", source_paper_id=electra.id, source_section_id="sec_elec_3"),
        Triple(head="ELECTRA", head_type="Method", relation="EVALUATED_ON", tail="GLUE", tail_type="Dataset", source_paper_id=electra.id, source_section_id="sec_elec_3"),
        Triple(head="ELECTRA", head_type="Method", relation="USES_METHOD", tail="Replaced Token Detection", tail_type="Method", source_paper_id=electra.id, source_section_id="sec_elec_2"),
    ]

    # Ingest into Neo4j
    for p, tr in [(roberta, triples_roberta), (t5, triples_t5), (electra, triples_electra)]:
        await neo4j_service.merge_paper(p)
        await neo4j_service.update_paper_status(p.id, PaperStatus.COMPLETE, 100.0)
        await neo4j_service.merge_triples(tr)
        logger.info(f"Ingested {p.id}: {p.title}")

    # Cross-paper SAME_AS edges connecting the 10 models
    cross_links = [
        ("BERT", "RoBERTa", 0.92),
        ("BERT", "ELECTRA", 0.88),
        ("Transformer", "T5", 0.86),
        ("GPT-3", "BERT", 0.80),
        ("RoBERTa", "XLNet", 0.85),
    ]

    async with neo4j_service.driver.session() as session:
        for a, b, sim in cross_links:
            await session.run(
                """MATCH (na {name: $name_a}), (nb {name: $name_b})
                   WHERE na <> nb
                   MERGE (na)-[:SAME_AS {similarity: $sim, source_paper_id: 'cross_linker'}]->(nb)""",
                name_a=a, name_b=b, sim=sim
            )
            
    logger.info("Successfully completed 10-paper graph seeding!")

if __name__ == "__main__":
    asyncio.run(run())
