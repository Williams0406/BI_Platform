from .expression import evaluate_expression

TOLERANCE = 1e-7

def evaluate_feasibility(compiled_model, values):
    violations = []
    for constraint in compiled_model["constraints"]:
        left = constraint["left"]["constant"] + sum(
            coefficient * float(values.get(variable, 0))
            for variable, coefficient in constraint["left"]["terms"]
        )
        right = float(constraint["right"])
        if constraint["sense"] == "LE" and left > right + TOLERANCE:
            violations.append({"constraint":constraint["name"],"left":left,"sense":"LE","right":right})
        elif constraint["sense"] == "GE" and left < right - TOLERANCE:
            violations.append({"constraint":constraint["name"],"left":left,"sense":"GE","right":right})
        elif constraint["sense"] == "EQ" and abs(left-right) > TOLERANCE:
            violations.append({"constraint":constraint["name"],"left":left,"sense":"EQ","right":right})
    for variable in compiled_model["variables"]:
        value = float(values.get(variable["name"], 0))
        if variable["lb"] is not None and value < variable["lb"] - TOLERANCE:
            violations.append({"variable":variable["name"],"detail":"below_lower_bound"})
        if variable["ub"] is not None and value > variable["ub"] + TOLERANCE:
            violations.append({"variable":variable["name"],"detail":"above_upper_bound"})
        if variable["type"] in {"INTEGER","BINARY"} and abs(value-round(value)) > TOLERANCE:
            violations.append({"variable":variable["name"],"detail":"not_integer"})
        if variable["type"] == "BINARY" and round(value) not in {0,1}:
            violations.append({"variable":variable["name"],"detail":"not_binary"})
    return len(violations) == 0, violations

def evaluate_baseline(compiled_model, baseline_values):
    if not baseline_values:
        return {
            "provided": False,
            "feasible": None,
            "objective_value": None,
            "violations": [],
        }
    feasible, violations = evaluate_feasibility(compiled_model, baseline_values)
    obj = compiled_model["objective"]["expression"]
    objective_value = obj["constant"] + sum(
        coef * float(baseline_values.get(name, 0))
        for name, coef in obj["terms"]
    )
    return {
        "provided": True,
        "feasible": feasible,
        "objective_value": float(objective_value),
        "violations": violations,
    }

def improvement(model_sense, optimized, baseline):
    if optimized is None or baseline is None:
        return None, None
    if model_sense == "MINIMIZE":
        absolute = baseline - optimized
    else:
        absolute = optimized - baseline
    percent = None if baseline == 0 else absolute / abs(baseline) * 100
    return float(absolute), None if percent is None else float(percent)
