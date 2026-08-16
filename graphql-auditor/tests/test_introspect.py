import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auditor.introspect import parse_schema, summarize_schema, run_introspection, IntrospectionError


# A small hand-built introspection response, standing in for a real
# server's reply. Covers: NON_NULL, LIST, nested list-of-non-null,
# a query with an ID-like arg (the kind of thing the IDOR flagger
# will care about later), and a mutation.
FIXTURE_RESPONSE = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": {"name": "Mutation"},
            "subscriptionType": None,
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "description": None,
                    "fields": [
                        {
                            "name": "user",
                            "args": [
                                {"name": "id", "type": {"kind": "NON_NULL", "name": None,
                                    "ofType": {"kind": "SCALAR", "name": "ID", "ofType": None}}}
                            ],
                            "type": {"kind": "OBJECT", "name": "User", "ofType": None},
                            "isDeprecated": False,
                        },
                        {
                            "name": "orders",
                            "args": [
                                {"name": "userId", "type": {"kind": "NON_NULL", "name": None,
                                    "ofType": {"kind": "SCALAR", "name": "ID", "ofType": None}}}
                            ],
                            "type": {
                                "kind": "NON_NULL", "name": None,
                                "ofType": {"kind": "LIST", "name": None,
                                    "ofType": {"kind": "NON_NULL", "name": None,
                                        "ofType": {"kind": "OBJECT", "name": "Order", "ofType": None}}}
                            },
                            "isDeprecated": False,
                        },
                    ],
                    "inputFields": None,
                    "interfaces": [],
                    "enumValues": None,
                    "possibleTypes": None,
                },
                {
                    "kind": "OBJECT",
                    "name": "Mutation",
                    "description": None,
                    "fields": [
                        {
                            "name": "deleteUser",
                            "args": [
                                {"name": "id", "type": {"kind": "NON_NULL", "name": None,
                                    "ofType": {"kind": "SCALAR", "name": "ID", "ofType": None}}}
                            ],
                            "type": {"kind": "SCALAR", "name": "Boolean", "ofType": None},
                            "isDeprecated": False,
                        }
                    ],
                    "inputFields": None,
                    "interfaces": [],
                    "enumValues": None,
                    "possibleTypes": None,
                },
                {
                    "kind": "OBJECT",
                    "name": "User",
                    "description": None,
                    "fields": [
                        {"name": "id", "args": [],
                         "type": {"kind": "NON_NULL", "name": None,
                             "ofType": {"kind": "SCALAR", "name": "ID", "ofType": None}},
                         "isDeprecated": False},
                        {"name": "email", "args": [],
                         "type": {"kind": "SCALAR", "name": "String", "ofType": None},
                         "isDeprecated": False},
                    ],
                    "inputFields": None,
                    "interfaces": [],
                    "enumValues": None,
                    "possibleTypes": None,
                },
                # Meta type that should be filtered out of the parsed result
                {"kind": "OBJECT", "name": "__Type", "description": None, "fields": [],
                 "inputFields": None, "interfaces": [], "enumValues": None, "possibleTypes": None},
            ],
        }
    }
}


class TestParseSchema(unittest.TestCase):
    def setUp(self):
        self.schema_map = parse_schema(FIXTURE_RESPONSE)

    def test_root_type_names(self):
        self.assertEqual(self.schema_map["query_type"], "Query")
        self.assertEqual(self.schema_map["mutation_type"], "Mutation")

    def test_meta_types_filtered(self):
        self.assertNotIn("__Type", self.schema_map["types"])

    def test_queries_extracted(self):
        self.assertIn("user", self.schema_map["queries"])
        self.assertIn("orders", self.schema_map["queries"])

    def test_mutations_extracted(self):
        self.assertIn("deleteUser", self.schema_map["mutations"])

    def test_nonnull_type_unwrapped(self):
        # `id: ID!` on the User type
        self.assertEqual(self.schema_map["types"]["User"]["fields"]["id"]["type"], "ID!")

    def test_nested_list_nonnull_unwrapped(self):
        # `orders(userId: ID!): [Order!]!`
        self.assertEqual(self.schema_map["queries"]["orders"]["type"], "[Order!]!")

    def test_args_captured(self):
        args = self.schema_map["queries"]["user"]["args"]
        self.assertEqual(args, [{"name": "id", "type": "ID!"}])

    def test_summarize_runs_without_error(self):
        summary = summarize_schema(self.schema_map)
        self.assertIn("user(id: ID!): User", summary)
        self.assertIn("deleteUser(id: ID!): Boolean", summary)


class TestRunIntrospectionErrors(unittest.TestCase):
    def test_raises_on_missing_schema(self):
        # Simulates introspection-disabled: server returns errors, no data.__schema
        class FakeResp:
            status_code = 200
            def json(self):
                return {"errors": [{"message": "introspection is disabled"}]}

        import auditor.introspect as introspect_mod
        original_post = introspect_mod.requests.post
        introspect_mod.requests.post = lambda *a, **k: FakeResp()
        try:
            with self.assertRaises(IntrospectionError):
                run_introspection("https://fake.example/graphql")
        finally:
            introspect_mod.requests.post = original_post


if __name__ == "__main__":
    unittest.main()
