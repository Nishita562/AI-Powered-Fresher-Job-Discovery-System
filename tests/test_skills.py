from src.skills import all_skills, extract_skills, normalize_skill_list


def test_aliases_map_to_canonical_names():
    found = extract_skills("Experience with sklearn, PowerBI, k8s and Node.js is a plus; ML basics required.")
    assert {"scikit-learn", "power bi", "kubernetes", "node.js", "machine learning"} <= set(found)


def test_word_boundaries():
    assert "java" not in extract_skills("Strong JavaScript skills")
    assert "javascript" in extract_skills("Strong JavaScript skills")
    assert extract_skills("We use C++ daily") == ["c++"]
    assert "c#" in extract_skills("C# and .NET")


def test_ambiguous_canonical_names_are_not_matched_alone():
    # "go", "r" and "c" are only matched through explicit aliases such as "golang".
    assert extract_skills("Go to market and ship features in a C grade team") == []
    assert "go" in extract_skills("Backend in Golang")


def test_empty_and_unknown_input():
    assert extract_skills("") == []
    assert extract_skills(None) == []
    assert normalize_skill_list(["Python", "  ", "Underwater Basket Weaving"]) == ["python", "underwater basket weaving"]
    assert normalize_skill_list("sql, ml; react") == ["machine learning", "react", "sql"]


def test_dictionary_size():
    assert len(all_skills()) >= 100
