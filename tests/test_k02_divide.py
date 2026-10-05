from kbflow.stages.k02_divide import build_boundary_matrix


def test_build_boundary_matrix():
    domains = [
        {
            "name": "调拨",
            "responsibility": "调拨单生命周期",
            "key_entities": ["调拨单"],
            "boundary_included": ["申请", "审批"],
            "boundary_excluded": ["采购"],
        },
    ]
    matrix = build_boundary_matrix(domains)
    assert matrix[0]["id"] == "D1"
    assert matrix[0]["name"] == "调拨"
    assert matrix[0]["key_entities"] == "调拨单"
    assert matrix[0]["boundary_included"] == "申请|审批"
    assert matrix[0]["boundary_excluded"] == "采购"
