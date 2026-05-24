from types import SimpleNamespace

from app.services.classification_service import merge_matrix_levels, rule_matches


def test_rule_matches_identifier_contains():
    entry = SimpleNamespace(identifier_key="user_id_card_number", field_name="证件", data_type="string")
    assert rule_matches({"type": "identifier_contains", "value": "card"}, entry)
    assert not rule_matches({"type": "identifier_contains", "value": "email"}, entry)


def test_merge_matrix_levels_last_wins():
    from sqlmodel import Session, SQLModel, create_engine

    from app.models import ClassificationMatrix, ProjectSpace, Tenant

    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        t = Tenant(name="T")
        session.add(t)
        session.flush()
        s = ProjectSpace(tenant_id=t.id, space_key="s", name="S")
        session.add(s)
        session.flush()
        session.add(
            ClassificationMatrix(
                tenant_id=t.id,
                project_space_id=s.id,
                name="m1",
                cells_json='[{"taxonomy_code":"A","sensitivity_level":"内部"}]',
            )
        )
        session.add(
            ClassificationMatrix(
                tenant_id=t.id,
                project_space_id=s.id,
                name="m2",
                cells_json='[{"taxonomy_code":"A","sensitivity_level":"秘密"}]',
            )
        )
        session.commit()
        m = merge_matrix_levels(session, t.id, s.id)
        assert m["A"] == "秘密"
