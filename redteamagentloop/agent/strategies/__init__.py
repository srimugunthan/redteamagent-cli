"""Attack strategy registry — import all strategies to trigger registration."""

from redteamagentloop.agent.strategies.base import STRATEGY_REGISTRY, AttackStrategy
from redteamagentloop.agent.strategies.finserv_specific import FinServSpecific
from redteamagentloop.agent.strategies.generic_attacks import (
    DirectJailbreak,
    PersonaHijack,
    DirectInjection,
    IndirectInjection,
    FewShotPoisoning,
    NestedInstruction,
    AdversarialSuffix,
    ContextOverflow,
    ObfuscatedRequest,
)
from redteamagentloop.agent.strategies.static_file import StaticFileStrategy
from redteamagentloop.agent.strategies.agent_specific import (
    ToolInjection,
    MemoryPoisoning,
    MultiHopManipulation,
    # category A
    AgentDirectSystemPromptOverride,
    AgentIndirectToolOutputInjection,
    AgentGoalHijackingRoleConfusion,
    AgentJailbreakNestedInstruction,
    AgentContextWindowOverflowInjection,
    # category B
    AgentParameterPoisoning,
    AgentToolChainingAbuse,
    AgentPrivilegeEscalationViaTool,
    AgentAdversarialToolOutputInjection,
    AgentToolEnumeration,
    # category C
    AgentMultiSessionMemoryPoisoning,
    AgentCompromisedInitialStateInjection,
    AgentStateRollbackAbuse,
    AgentCrossSessionMemoryLeakage,
    # category E
    AgentChainOfThoughtManipulation,
    AgentPlanSabotageAdversarialSubGoal,
    AgentInfiniteLoopPlanningStall,
    AgentFalsePremiseInjectionReasoning,
    # category F
    AgentSystemPromptExfiltration,
    AgentMemoryKnowledgeBaseExfiltration,
    AgentToolCredentialExfiltration,
)
from redteamagentloop.agent.strategies.rag_specific import (
    # context
    RAGConflictingChunkInjection,
    RAGContextStuffing,
    RAGDistractorDocument,
    RAGLongContextDilution,
    RAGPositionBiasProbe,
    # data leakage
    RAGCrossUserIsolation,
    RAGMembershipInference,
    RAGPiiExfiltration,
    RAGVerbatimExtraction,
    # faithfulness
    RAGHallucinationUnderAmbiguity,
    RAGRefusalBypass,
    RAGSourceMisattribution,
    RAGSycophancyOverride,
    RAGTemporalConfusion,
    # injection
    RAGDirectPromptInjection,
    RAGIndirectPromptInjection,
    RAGInstructionOverride,
    RAGRoleConfusion,
    RAGSystemPromptExtraction,
    # retriever
    RAGEmbeddingInversion,
    RAGEmptyRetrievalProbe,
    RAGKeywordInjection,
    RAGQueryDrift,
    RAGSparseDenseMismatch,
)

__all__ = [
    "STRATEGY_REGISTRY",
    "AttackStrategy",
    "DirectJailbreak",
    "PersonaHijack",
    "DirectInjection",
    "IndirectInjection",
    "FewShotPoisoning",
    "NestedInstruction",
    "AdversarialSuffix",
    "ContextOverflow",
    "ObfuscatedRequest",
    "FinServSpecific",
    "StaticFileStrategy",
    "ToolInjection",
    "MemoryPoisoning",
    "MultiHopManipulation",
    # agent category A
    "AgentDirectSystemPromptOverride",
    "AgentIndirectToolOutputInjection",
    "AgentGoalHijackingRoleConfusion",
    "AgentJailbreakNestedInstruction",
    "AgentContextWindowOverflowInjection",
    # agent category B
    "AgentParameterPoisoning",
    "AgentToolChainingAbuse",
    "AgentPrivilegeEscalationViaTool",
    "AgentAdversarialToolOutputInjection",
    "AgentToolEnumeration",
    # agent category C
    "AgentMultiSessionMemoryPoisoning",
    "AgentCompromisedInitialStateInjection",
    "AgentStateRollbackAbuse",
    "AgentCrossSessionMemoryLeakage",
    # agent category E
    "AgentChainOfThoughtManipulation",
    "AgentPlanSabotageAdversarialSubGoal",
    "AgentInfiniteLoopPlanningStall",
    "AgentFalsePremiseInjectionReasoning",
    # agent category F
    "AgentSystemPromptExfiltration",
    "AgentMemoryKnowledgeBaseExfiltration",
    "AgentToolCredentialExfiltration",
    # RAG-specific
    "RAGConflictingChunkInjection",
    "RAGContextStuffing",
    "RAGDistractorDocument",
    "RAGLongContextDilution",
    "RAGPositionBiasProbe",
    "RAGCrossUserIsolation",
    "RAGMembershipInference",
    "RAGPiiExfiltration",
    "RAGVerbatimExtraction",
    "RAGHallucinationUnderAmbiguity",
    "RAGRefusalBypass",
    "RAGSourceMisattribution",
    "RAGSycophancyOverride",
    "RAGTemporalConfusion",
    "RAGDirectPromptInjection",
    "RAGIndirectPromptInjection",
    "RAGInstructionOverride",
    "RAGRoleConfusion",
    "RAGSystemPromptExtraction",
    "RAGEmbeddingInversion",
    "RAGEmptyRetrievalProbe",
    "RAGKeywordInjection",
    "RAGQueryDrift",
    "RAGSparseDenseMismatch",
]
