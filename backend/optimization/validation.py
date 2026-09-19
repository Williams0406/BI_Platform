from .expression import OptimizationExpressionError, validate_expression
from .models import OptimizationObjective

def validate_model_definition(model):
    errors = []
    variable_names = set(model.variables.values_list("name", flat=True))
    parameter_names = set(model.parameters.values_list("name", flat=True))

    if not variable_names:
        errors.append("El modelo no tiene variables.")

    try:
        objective = model.objective
    except OptimizationObjective.DoesNotExist:
        errors.append("El modelo no tiene objetivo.")
        objective = None

    if objective:
        try:
            validate_expression(
                objective.expression,
                variable_names,
                parameter_names,
            )
        except OptimizationExpressionError as exc:
            errors.append(f"Objetivo inválido: {exc}")

    for constraint in model.constraints.filter(enabled=True):
        try:
            validate_expression(
                constraint.left_expression,
                variable_names,
                parameter_names,
            )
            if isinstance(constraint.right_value, dict):
                if (
                    set(constraint.right_value) != {"parameter"}
                    or constraint.right_value["parameter"] not in parameter_names
                ):
                    raise OptimizationExpressionError(
                        "right_value parametrizado inválido."
                    )
            elif not isinstance(constraint.right_value, (int, float)):
                raise OptimizationExpressionError(
                    "right_value debe ser número o parámetro."
                )
        except OptimizationExpressionError as exc:
            errors.append(f"Restricción {constraint.name}: {exc}")

    for variable in model.variables.all():
        for label, value in [
            ("lower_bound", variable.lower_bound),
            ("upper_bound", variable.upper_bound),
        ]:
            if value is None:
                continue
            if isinstance(value, dict):
                if (
                    set(value) != {"parameter"}
                    or value["parameter"] not in parameter_names
                ):
                    errors.append(
                        f"Variable {variable.name}: {label} parametrizado inválido."
                    )
            elif not isinstance(value, (int, float)):
                errors.append(
                    f"Variable {variable.name}: {label} inválido."
                )

    return {
        "valid": not errors,
        "errors": errors,
        "counts": {
            "parameters": model.parameters.count(),
            "variables": model.variables.count(),
            "constraints": model.constraints.filter(enabled=True).count(),
            "solver_configs": model.solver_configs.count(),
            "scenarios": model.scenarios.count(),
        },
    }
