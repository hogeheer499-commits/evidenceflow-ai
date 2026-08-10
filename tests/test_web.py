from evidenceflow.web import render_dashboard


def test_dashboard_escapes_case_content_and_requires_named_reviewer() -> None:
    page = render_dashboard(
        [
            {
                "case_id": 'case"><script>alert(1)</script>',
                "title": "<unsafe>",
                "state": "pending_approval",
                "risk": "medium",
                "reviewer": None,
                "receipt": None,
            }
        ],
        audit_valid=True,
        csrf_token="csrf-token",
    )
    assert "<script>alert(1)</script>" not in page
    assert "&lt;unsafe&gt;" in page
    assert 'name="reviewer"' in page
    assert 'value="csrf-token"' in page


def test_dashboard_only_offers_publish_after_approval() -> None:
    page = render_dashboard(
        [
            {
                "case_id": "case-1",
                "title": "Approved case",
                "state": "approved",
                "risk": "low",
                "reviewer": "reviewer@kleinekoe.nl",
                "receipt": None,
            }
        ],
        audit_valid=True,
        csrf_token="csrf-token",
    )
    assert "Create approved export" in page
    assert 'action="/approve"' not in page
