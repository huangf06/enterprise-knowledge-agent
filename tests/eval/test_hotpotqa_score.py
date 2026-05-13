from src.eval.hotpotqa_score import exact_match, f1_score, score


def test_normalization_handles_articles_punctuation_case():
    assert exact_match("The Beatles.", "beatles") == 1.0
    assert exact_match("A wedding ring", "wedding ring") == 1.0


def test_f1_partial_overlap():
    f1, p, r = f1_score("Barack Hussein Obama", "Barack Obama")
    # tokens: pred=[barack hussein obama], gold=[barack obama]; overlap=2
    # precision = 2/3, recall = 2/2 -> f1 = 0.8
    assert round(f1, 3) == 0.8
    assert round(p, 3) == round(2 / 3, 3)
    assert r == 1.0


def test_f1_no_overlap():
    f1, p, r = f1_score("Pluto", "Mars")
    assert f1 == 0.0 and p == 0.0 and r == 0.0


def test_yes_no_strict_match():
    # yes vs anything-not-yes is zero (matches the upstream sentinel rule)
    assert f1_score("yes", "no")[0] == 0.0
    assert exact_match("yes", "yes") == 1.0
    assert score("yes.", "yes").em == 1.0


def test_em_independent_of_f1_partial():
    s = score("Barack Hussein Obama", "Barack Obama")
    assert s.em == 0.0
    assert s.f1 > 0.5
