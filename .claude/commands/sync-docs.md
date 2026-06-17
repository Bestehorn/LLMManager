---
description: Reconcile docs/ with the current implementation and refresh docs/forLLMConsumption.md.
allowed-tools: Bash, Read, Edit, Grep, Glob
---
Ported from `.kiro/hooks/sync-documentation.kiro.hook`. Synchronize documentation with the
current implementation.

1. **Read all documentation**: everything in `docs/` (forLLMConsumption.md, ProjectStructure.md,
   MIGRATION_GUIDE.md, caching.md, MODEL_NAME_RESOLUTION_GUIDE.md, etc.), `README.md`, the
   docstrings in `src/bestehorn_llmmanager/`, and `examples/`. Note the documented architecture,
   components, workflows, and API usage patterns.
2. **Analyze the current implementation**: walk `src/bestehorn_llmmanager/`, `scripts/`, and
   `examples/`. Identify the major components: `LLMManager`, `ParallelLLMManager`, `MessageBuilder`,
   `BedrockResponse`, `UnifiedModelManager`, `ModelManager`, `CRISManager`, and the catalog system
   (`BedrockCatalog`, `APIFetcher`, `CacheManager`, `BundledLoader`, `Transformer`). Note current
   class/function signatures.
3. **Identify conflicts and deviations**: components in docs but not code (removed/renamed),
   components in code but undocumented (new), outdated descriptions/workflows, examples that no
   longer match current signatures, breaking/deprecated features still documented.
4. **Update documentation** to match the implementation: add docs for new components, mark obsolete
   info deprecated/removed, fix code examples and import statements, refresh setup/installation
   instructions, update `examples/`.
5. **Consolidate for LLM consumption**: refresh `docs/forLLMConsumption.md` so it provides complete
   context for an AI assistant — project overview, architecture, key components, directory structure,
   common commands, testing strategy, the catalog system, multi-model/multi-region failover, prompt
   caching, and the note that `src/bestehorn_llmmanager/_version.py` is auto-generated (never modify).
6. **Update README.md**: current install instructions, up-to-date usage examples, accurate feature
   list, valid badges/links.
7. **Report**: files updated, the major changes per file, deviations that could not be resolved
   automatically, and anything needing manual review.

**Project-specific context**: package `bestehorn-llmmanager`; auto-generated
`src/bestehorn_llmmanager/_version.py` (never modify, always exclude from checks).
