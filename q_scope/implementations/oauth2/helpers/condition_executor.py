from typing import Sequence, Mapping, Any
from q_scope.implementations.datastrutures import Result, SuccessResult
from q_scope.implementations.oauth2.templates.base import Condition

class ConditionChain:
    """
    Executes a sequence of Conditions in order.

    Stops at the first FailedResult.
    """

    def __init__(self, conditions: Sequence[Condition]):
        self._conditions = list(conditions)

    async def execute(
        self,
        *,
        context: Mapping[str, Any],
        ray_id: str,
    ) -> Result:
        for condition in self._conditions:
            result = await condition.validate(
                context=context,
                ray_id=ray_id,
            )

            # Business failure → short-circuit
            if result.status is False:
                return result

        # All conditions passed
        return SuccessResult( #type: ignore
            ray_id=ray_id,
            client_message=None,
        )

