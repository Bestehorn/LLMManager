---
inclusion: always
---

# Design Principles

1. **Pre-Design Reading**: Re-read `docs/ProjectStructure.md` before any design work

2. **Modularization Priority**: 
   - Separate functions into independent pieces
   - Use inheritance for modularity
   - Review existing components for reuse

3. **Avoid Breaking Changes**: 
   - Review existing functions before changes
   - Flag any breaking changes explicitly

4. **Design Patterns**: Use patterns (Factory, Strategy, Repository, etc.) for maintainability

5. **AWS Bedrock Focus**: This project is specifically for AWS Bedrock LLM management
   - Multi-model support with automatic failover
   - Multi-region support with intelligent routing
   - Fluent MessageBuilder for multi-modal content
   - Parallel processing capabilities
