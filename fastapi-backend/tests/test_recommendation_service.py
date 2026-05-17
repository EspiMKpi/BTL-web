"""
Tests for recommendation_service — TF-IDF inference, lazy load, artifact validation.

Uses the `artifact_root` + `build_artifacts` fixtures from conftest to write
tiny TF-IDF models into a tmp dir and point the service at them.
"""

import json

import pytest

from app.services import recommendation_service as rs


class TestSimilarTo:
    def test_returns_top_n_excluding_self(self, artifact_root, build_artifacts):
        # Three near-duplicate sci-fi soups + one unrelated cooking soup.
        # Query item 1 should rank items 2 and 3 above item 4.
        build_artifacts(artifact_root, "movie", [
            (1, "Alpha", "space stars galaxy aliens cosmic"),
            (2, "Beta",  "space stars galaxy aliens planets"),
            (3, "Gamma", "space stars galaxy orbit"),
            (4, "Delta", "cooking pasta italian recipes kitchen"),
        ])
        result = rs.similar_to("movie", 1, top_n=2)
        assert 1 not in result, "self should be excluded"
        assert set(result) == {2, 3}

    def test_unknown_id_returns_empty(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "space stars"),
            (2, "B", "ocean waves"),
        ])
        assert rs.similar_to("movie", 99999) == []

    def test_no_positive_similarity_returns_empty(self, artifact_root, build_artifacts):
        # Disjoint token sets → cosine sim = 0 → nothing passes the >0 filter.
        build_artifacts(artifact_root, "movie", [
            (1, "A", "aardvark"),
            (2, "B", "zebra"),
        ])
        assert rs.similar_to("movie", 1) == []

    def test_top_n_larger_than_corpus(self, artifact_root, build_artifacts):
        # top_n >= len(sims) hits the argsort branch instead of argpartition.
        build_artifacts(artifact_root, "movie", [
            (1, "A", "space stars galaxy"),
            (2, "B", "space stars planets"),
            (3, "C", "space ships orbit"),
        ])
        result = rs.similar_to("movie", 1, top_n=50)
        assert len(result) <= 2  # at most N-1 (self excluded)
        assert 1 not in result


class TestContentTypeValidation:
    def test_rejects_unknown_content_type(self, artifact_root):
        with pytest.raises(ValueError, match="unsupported content_type"):
            rs.similar_to("music", 1)

    def test_loads_movie_and_series_independently(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie",  [(1, "A", "foo bar"), (2, "B", "foo baz")])
        build_artifacts(artifact_root, "series", [(10, "A", "foo bar"), (20, "B", "foo baz")])
        assert rs.similar_to("movie", 1)
        assert rs.similar_to("series", 10)
        assert "movie" in rs._STATE
        assert "series" in rs._STATE


class TestLoad:
    def test_missing_artifacts_raises_not_trained(self, artifact_root):
        # artifact_root exists but contains no metadata.json
        with pytest.raises(rs.RecommenderNotTrained):
            rs.similar_to("movie", 1)

    def test_rejects_wrong_kind(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie",
                        [(1, "A", "foo bar"), (2, "B", "foo baz")],
                        kind="bogus_v0")
        with pytest.raises(RuntimeError, match="kind mismatch"):
            rs.similar_to("movie", 1)

    def test_rejects_content_type_mismatch(self, artifact_root, build_artifacts):
        # Build under movies/ but tamper the metadata to claim series.
        build_artifacts(artifact_root, "movie", [(1, "A", "foo bar"), (2, "B", "foo baz")])
        meta_path = artifact_root / "movies" / "metadata.json"
        meta = json.loads(meta_path.read_text())
        meta["content_type"] = "series"
        meta_path.write_text(json.dumps(meta))
        with pytest.raises(RuntimeError, match="content_type mismatch"):
            rs.similar_to("movie", 1)


class TestReload:
    def test_reload_picks_up_new_artifacts(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "space stars"),
            (2, "B", "space planets"),
        ])
        assert rs.similar_to("movie", 1) == [2]

        # Rebuild with item 3 replacing item 2; without reload, cache returns stale.
        build_artifacts(artifact_root, "movie", [
            (1, "A", "space stars"),
            (3, "C", "space planets"),
        ])
        assert rs.similar_to("movie", 1) == [2]  # stale

        rs.reload("movie")
        assert rs.similar_to("movie", 1) == [3]  # fresh

    def test_reload_all_drops_every_content_type(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie",  [(1, "A", "foo bar"), (2, "B", "foo baz")])
        build_artifacts(artifact_root, "series", [(10, "A", "foo bar"), (20, "B", "foo baz")])
        rs.similar_to("movie", 1)
        rs.similar_to("series", 10)
        assert len(rs._STATE) == 2

        rs.reload(None)
        assert rs._STATE == {}

    def test_reload_rejects_bad_content_type(self, artifact_root):
        with pytest.raises(ValueError, match="unsupported content_type"):
            rs.reload("music")


class TestLoadedState:
    def test_empty_before_first_call(self, artifact_root):
        assert rs.loaded_state() == {}

    def test_populated_after_call(self, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [(1, "A", "foo bar"), (2, "B", "foo baz")])
        rs.similar_to("movie", 1)
        state = rs.loaded_state()
        assert "movie" in state
        assert state["movie"]["metadata"]["content_type"] == "movie"
        assert state["movie"]["metadata"]["kind"] == rs.EXPECTED_KIND
        assert "loaded_at" in state["movie"]
