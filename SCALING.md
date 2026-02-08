"""
How AgentZero scales to multi-agent systems:

- Each agent is an independent LangGraph instance with its own local memory, skills, and audit log.
- Agents communicate via local IPC (e.g., Unix sockets, named pipes, or local message bus), never over the cloud.
- Shared memory (if needed) is implemented as a local, permissioned database (e.g., SQLite or shared vector DB), with strict access control and audit.
- Multi-agent workflows are orchestrated by a supervisor agent or a meta-graph, which delegates tasks and aggregates results.
- All agent-to-agent messages are logged and can be encrypted for zero-knowledge sync.
- Adding zero-knowledge sync: Use local encryption (e.g., Fernet/AES) for all shared data, and sync only encrypted blobs between devices. Decryption keys never leave the user's device.
- Policy enforcement and audit remain local and agent-specific, ensuring privacy and compliance.

This architecture supports scaling from single-user to small team/enterprise deployments, while maintaining local-first, privacy-preserving guarantees.
