from .expression import compile_terms, resolve_value

def compile_model(model, parameters):
    variables = []
    variable_names = set()
    for variable in model.variables.all():
        variable_names.add(variable.name)
        variables.append({
            "name": variable.name,
            "type": variable.variable_type,
            "lb": resolve_value(variable.lower_bound, parameters),
            "ub": None if variable.upper_bound is None else resolve_value(variable.upper_bound, parameters),
        })

    objective = model.objective
    constraints = []
    for constraint in model.constraints.filter(enabled=True):
        constraints.append({
            "name": constraint.name,
            "left": compile_terms(constraint.left_expression, parameters),
            "sense": constraint.sense,
            "right": resolve_value(constraint.right_value, parameters),
        })

    return {
        "problem_type": model.problem_type,
        "variables": variables,
        "objective": {
            "name": objective.name,
            "sense": objective.sense,
            "expression": compile_terms(objective.expression, parameters),
        },
        "constraints": constraints,
    }
