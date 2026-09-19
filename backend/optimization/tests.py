from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase

from datasources.models import DataAsset
from workspaces.models import Membership, Organization, Workspace

from .baseline import evaluate_baseline, improvement
from .expression import evaluate_expression, validate_expression
from .models import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationParameter,
    OptimizationScenario,
    OptimizationVariable,
)


class ExpressionTests(SimpleTestCase):
    def test_parameterized_expression(self):
        expression = {
            "constant": 5,
            "terms": [
                {"variable": "x", "coefficient": {"parameter": "cost"}},
                {"variable": "y", "coefficient": 2},
            ],
        }
        validate_expression(expression, {"x", "y"}, {"cost"})
        value = evaluate_expression(
            expression,
            {"x": 3, "y": 4},
            {"cost": 10},
        )
        self.assertEqual(value, 43.0)

    def test_baseline_improvement_for_minimization(self):
        absolute, percent = improvement("MINIMIZE", 80, 100)
        self.assertEqual(absolute, 20)
        self.assertEqual(percent, 20)


class OptimizationDefinitionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="optimization@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Optimization Org",
            slug="optimization-org",
            created_by=user,
        )
        Membership.objects.create(
            organization=org,
            user=user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=org,
            name="OR",
            slug="or",
            created_by=user,
        )
        self.model = OptimizationModel.objects.create(
            workspace=self.workspace,
            name="Production Mix",
            problem_type=OptimizationModel.ProblemType.LP,
            created_by=user,
        )
        OptimizationParameter.objects.create(
            model=self.model,
            name="capacity",
            default_value=100,
        )
        OptimizationVariable.objects.create(
            model=self.model,
            name="x",
            variable_type=OptimizationVariable.VariableType.CONTINUOUS,
            lower_bound=0,
        )
        OptimizationVariable.objects.create(
            model=self.model,
            name="y",
            variable_type=OptimizationVariable.VariableType.CONTINUOUS,
            lower_bound=0,
        )
        OptimizationObjective.objects.create(
            model=self.model,
            name="Profit",
            sense=OptimizationObjective.Sense.MAXIMIZE,
            expression={
                "terms": [
                    {"variable": "x", "coefficient": 5},
                    {"variable": "y", "coefficient": 4},
                ]
            },
        )
        OptimizationConstraint.objects.create(
            model=self.model,
            name="Capacity",
            left_expression={
                "terms": [
                    {"variable": "x", "coefficient": 2},
                    {"variable": "y", "coefficient": 1},
                ]
            },
            sense=OptimizationConstraint.Sense.LE,
            right_value={"parameter": "capacity"},
        )

    def test_baseline_feasibility(self):
        compiled = {
            "variables": [
                {"name": "x", "type": "CONTINUOUS", "lb": 0, "ub": None},
                {"name": "y", "type": "CONTINUOUS", "lb": 0, "ub": None},
            ],
            "objective": {
                "sense": "MAXIMIZE",
                "expression": {
                    "constant": 0,
                    "terms": [("x", 5), ("y", 4)],
                },
            },
            "constraints": [
                {
                    "name": "Capacity",
                    "left": {
                        "constant": 0,
                        "terms": [("x", 2), ("y", 1)],
                    },
                    "sense": "LE",
                    "right": 100,
                }
            ],
        }
        result = evaluate_baseline(compiled, {"x": 20, "y": 30})
        self.assertTrue(result["feasible"])
        self.assertEqual(result["objective_value"], 220)
