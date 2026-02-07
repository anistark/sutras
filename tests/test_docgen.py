"""Tests for skill documentation generator."""

from pathlib import Path

from sutras.core.abi import (
    CapabilitiesConfig,
    DependencyConfig,
    DistributionMetadata,
    EvalConfig,
    SutrasABI,
    TestCase,
    TestConfig,
)
from sutras.core.docgen import generate_docs, write_docs
from sutras.core.skill import Skill, SkillMetadata


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill for unit testing",
    instructions: str = "Do the thing.",
    abi: SutrasABI | None = None,
    supporting_files: dict[str, Path] | None = None,
) -> Skill:
    return Skill(
        path=Path("/fake/path"),
        metadata=SkillMetadata(name=name, description=description),
        instructions=instructions,
        abi=abi,
        supporting_files=supporting_files or {},
    )


class TestGenerateDocs:
    def test_minimal_skill(self):
        doc = generate_docs(_make_skill())
        assert "# Test Skill" in doc
        assert "A test skill for unit testing" in doc
        assert "Do the thing." in doc

    def test_title_formatting(self):
        doc = generate_docs(_make_skill(name="my-cool-skill"))
        assert "# My Cool Skill" in doc

    def test_version_badge(self):
        abi = SutrasABI(version="2.1.0")
        doc = generate_docs(_make_skill(abi=abi))
        assert "**Version:** 2.1.0" in doc

    def test_author_badge(self):
        abi = SutrasABI(version="1.0.0", author="Alice")
        doc = generate_docs(_make_skill(abi=abi))
        assert "**Author:** Alice" in doc

    def test_license_badge(self):
        abi = SutrasABI(version="1.0.0", license="Apache-2.0")
        doc = generate_docs(_make_skill(abi=abi))
        assert "**License:** Apache-2.0" in doc

    def test_allowed_tools(self):
        skill = _make_skill()
        skill.metadata.allowed_tools = ["Read", "Write"]
        doc = generate_docs(skill)
        assert "`Read`" in doc
        assert "`Write`" in doc

    def test_abi_capabilities_tools(self):
        abi = SutrasABI(
            version="1.0.0",
            capabilities=CapabilitiesConfig(tools=["Bash", "Read"]),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "`Bash`" in doc
        assert "`Read`" in doc

    def test_dependencies_as_configs(self):
        abi = SutrasABI(
            version="1.0.0",
            capabilities=CapabilitiesConfig(
                dependencies=[
                    DependencyConfig(name="@utils/helper", version="^1.0.0"),
                ]
            ),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "`@utils/helper`" in doc
        assert "(^1.0.0)" in doc

    def test_dependencies_as_strings(self):
        abi = SutrasABI(
            version="1.0.0",
            capabilities=CapabilitiesConfig(dependencies=["@tools/common", "@tools/other"]),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "`@tools/common`" in doc
        assert "`@tools/other`" in doc

    def test_optional_dependency(self):
        abi = SutrasABI(
            version="1.0.0",
            capabilities=CapabilitiesConfig(
                dependencies=[
                    DependencyConfig(name="@opt/dep", version="^2.0.0", optional=True),
                ]
            ),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "*(optional)*" in doc

    def test_distribution_metadata(self):
        abi = SutrasABI(
            version="1.0.0",
            repository="https://github.com/test/repo",
            distribution=DistributionMetadata(
                tags=["demo", "test"],
                category="utilities",
                keywords=["hello"],
                homepage="https://example.com",
            ),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "https://github.com/test/repo" in doc
        assert "utilities" in doc
        assert "demo" in doc
        assert "https://example.com" in doc

    def test_test_cases(self):
        abi = SutrasABI(
            version="1.0.0",
            tests=TestConfig(
                cases=[
                    TestCase(name="basic-test", description="Runs the basics"),
                    TestCase(name="edge-case"),
                ]
            ),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "## Tests" in doc
        assert "basic-test" in doc
        assert "Runs the basics" in doc
        assert "edge-case" in doc

    def test_eval_config(self):
        abi = SutrasABI(
            version="1.0.0",
            eval=EvalConfig(
                framework="ragas",
                metrics=["faithfulness", "relevancy"],
                threshold=0.8,
                dataset="tests/eval/data.json",
            ),
        )
        doc = generate_docs(_make_skill(abi=abi))
        assert "## Evaluation" in doc
        assert "ragas" in doc
        assert "faithfulness" in doc
        assert "0.8" in doc
        assert "tests/eval/data.json" in doc

    def test_supporting_markdown_files(self, tmp_path: Path):
        examples = tmp_path / "examples.md"
        examples.write_text("# Examples\n\nSome examples here.")
        readme = tmp_path / "README.txt"
        readme.write_text("not included")

        skill = _make_skill(
            supporting_files={
                "examples.md": examples,
                "README.txt": readme,
            }
        )
        doc = generate_docs(skill, include_supporting=True)
        assert "Some examples here." in doc
        assert "not included" not in doc

    def test_exclude_supporting(self, tmp_path: Path):
        examples = tmp_path / "examples.md"
        examples.write_text("# Examples\n\nHidden content.")

        skill = _make_skill(supporting_files={"examples.md": examples})
        doc = generate_docs(skill, include_supporting=False)
        assert "Hidden content." not in doc

    def test_no_instructions_section_when_empty(self):
        doc = generate_docs(_make_skill(instructions=""))
        assert "## Instructions" not in doc

    def test_ends_with_newline(self):
        doc = generate_docs(_make_skill())
        assert doc.endswith("\n")

    def test_no_tools_section_when_none(self):
        doc = generate_docs(_make_skill())
        assert "## Tools" not in doc


class TestWriteDocs:
    def test_write_to_file(self, tmp_path: Path):
        out = tmp_path / "output.md"
        result = write_docs(_make_skill(), out)
        assert result == out
        assert result.exists()
        assert "# Test Skill" in result.read_text()

    def test_write_to_directory(self, tmp_path: Path):
        result = write_docs(_make_skill(name="my-skill"), tmp_path)
        assert result == tmp_path / "my-skill.md"
        assert result.exists()

    def test_creates_parent_dirs(self, tmp_path: Path):
        out = tmp_path / "nested" / "deep" / "doc.md"
        result = write_docs(_make_skill(), out)
        assert result.exists()

    def test_content_matches_generate(self):
        import tempfile

        skill = _make_skill()
        expected = generate_docs(skill)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "doc.md"
            write_docs(skill, out)
            assert out.read_text() == expected
