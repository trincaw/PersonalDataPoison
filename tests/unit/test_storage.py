import pytest
import json
import tempfile
from pathlib import Path
from uuid import uuid4

from identity.generator import IdentityGenerator
from identity.persistence import IdentityStore
from identity.scoring import IdentityScorer


class TestIdentityStore:

    @pytest.fixture
    def store(self, tmp_path):
        return IdentityStore(tmp_path / "identities")

    @pytest.fixture
    def generator(self):
        return IdentityGenerator()

    def test_save_and_load(self, store, generator):
        identity = generator.create()
        store.save(identity)
        loaded = store.load(identity.id)
        assert loaded is not None
        assert loaded.alias == identity.alias

    def test_load_all(self, store, generator):
        for _ in range(3):
            store.save(generator.create())
        all_ids = store.load_all()
        assert len(all_ids) == 3

    def test_delete(self, store, generator):
        identity = generator.create()
        store.save(identity)
        assert store.delete(identity.id)
        assert store.load(identity.id) is None

    def test_find_by_alias(self, store, generator):
        identity = generator.create()
        store.save(identity)
        found = store.find_by_alias(identity.alias)
        assert found is not None
        assert found.id == identity.id

    def test_count(self, store, generator):
        assert store.count() == 0
        store.save(generator.create())
        assert store.count() == 1


class TestIdentityScorer:

    def test_score_range(self):
        generator = IdentityGenerator()
        scorer = IdentityScorer()
        identity = generator.create()
        score = scorer.score(identity)
        assert 0.0 <= score <= 1.0

    def test_new_identity_low_score(self):
        generator = IdentityGenerator()
        scorer = IdentityScorer()
        identity = generator.create()
        score = scorer.score(identity)
        # New identity should have a relatively low score
        assert score < 0.8
