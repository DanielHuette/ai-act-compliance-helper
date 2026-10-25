"""English accuracy of the classification on the company questions.

Context: English descriptions reach the same rule set through the English purpose sentences and
vocabularies; measured exactly like the German run, so the two rates are comparable. | Input:
English side of data/evaluation/company_questions.yaml, both local models | Output: pass when
English accuracy reaches the gate.
"""

from __future__ import annotations

import pytest
from test_purposes import ACCURACY_GATE, measure_accuracy

from compliance_helper.i18n import Language


@pytest.mark.slow
def test_accuracy_on_english_company_questions() -> None:
    """English accuracy with embedder and reranker; same gate as German."""
    correct, wrong = measure_accuracy(Language.EN)
    assert correct >= ACCURACY_GATE, f"only {correct} of 100 correct:\n" + "\n".join(wrong)
