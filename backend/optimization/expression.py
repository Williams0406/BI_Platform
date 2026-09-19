from dataclasses import dataclass

class OptimizationExpressionError(ValueError):
    pass

def resolve_value(value, parameters):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, dict) and set(value) == {"parameter"}:
        name = value["parameter"]
        if name not in parameters:
            raise OptimizationExpressionError(f"Parámetro no resuelto: {name}")
        return float(parameters[name])
    raise OptimizationExpressionError(f"Valor no soportado: {value!r}")

def validate_expression(expression, variable_names, parameter_names):
    if not isinstance(expression, dict):
        raise OptimizationExpressionError("La expresión debe ser un objeto JSON.")
    allowed = {"constant", "terms"}
    unknown = set(expression) - allowed
    if unknown:
        raise OptimizationExpressionError("Claves no soportadas: " + ", ".join(sorted(unknown)))
    resolve_value(expression.get("constant", 0), {name: 0 for name in parameter_names})
    terms = expression.get("terms", [])
    if not isinstance(terms, list):
        raise OptimizationExpressionError("terms debe ser una lista.")
    for term in terms:
        if not isinstance(term, dict):
            raise OptimizationExpressionError("Cada term debe ser un objeto.")
        if term.get("variable") not in variable_names:
            raise OptimizationExpressionError(f"Variable desconocida: {term.get('variable')}")
        coefficient = term.get("coefficient", 1)
        if isinstance(coefficient, dict):
            if set(coefficient) != {"parameter"} or coefficient["parameter"] not in parameter_names:
                raise OptimizationExpressionError("Coeficiente parametrizado inválido.")
        elif not isinstance(coefficient, (int, float)):
            raise OptimizationExpressionError("Coeficiente inválido.")
    return True

def evaluate_expression(expression, variable_values, parameters):
    total = resolve_value(expression.get("constant", 0), parameters)
    for term in expression.get("terms", []):
        variable = term["variable"]
        coefficient = resolve_value(term.get("coefficient", 1), parameters)
        if variable not in variable_values:
            raise OptimizationExpressionError(f"Valor faltante para variable: {variable}")
        total += coefficient * float(variable_values[variable])
    return total

def compile_terms(expression, parameters):
    return {
        "constant": resolve_value(expression.get("constant", 0), parameters),
        "terms": [
            (
                term["variable"],
                resolve_value(term.get("coefficient", 1), parameters),
            )
            for term in expression.get("terms", [])
        ],
    }
