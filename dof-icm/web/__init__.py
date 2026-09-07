"""Human-evaluation web UI for the DOF-ICM file-based agent.

Adapted from ``CodeandoGuadalajara/dof-rag/human_eval`` (MIT). The UI keeps
the upstream workflow (auth, quota, review, publish, feedback); answers are
produced by the DOF-ICM agent over the plain-markdown corpus (see
``icm_executor``) instead of the upstream ``dof_db`` vector stack.
"""

from .contracts import FeedbackRequest, RunRequest
from .icm_executor import IcmExecutorConfig, IcmRunExecutor
from .service import EvaluationService, PublicExecutionError
from .store import EvaluationStore

__all__ = [
    "EvaluationService",
    "EvaluationStore",
    "FeedbackRequest",
    "PublicExecutionError",
    "RunRequest",
    "IcmExecutorConfig",
    "IcmRunExecutor",
]
