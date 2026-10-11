from eval.corpus import get_corpus, get_core_papers, get_ood_papers, get_eval_papers


def test_eval_papers_no_duplicates_and_no_excluded():
    corpus = get_corpus()
    core = get_core_papers()
    ood = get_ood_papers()
    eval_papers = get_eval_papers()
    excluded = set(corpus.get("excluded", []))

    # Must be combination of core and ood
    assert eval_papers == core + ood

    # Must have no duplicates
    assert len(eval_papers) == len(set(eval_papers))

    # None of the excluded IDs can appear in eval_papers
    for p in eval_papers:
        assert p not in excluded, f"Paper {p} is in excluded list!"

    # None of the disk duplicates can appear in eval_papers
    disk_dups = set(corpus.get("duplicates_on_disk_only", []))
    for p in eval_papers:
        assert p not in disk_dups, f"Paper {p} is in duplicates_on_disk_only!"
