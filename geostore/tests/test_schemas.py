from geostore.models import Layer
from geostore.db.tmp import test
from geostore.db.schemas import schema_to_schemamodel
from django.test import TestCase

schema_complex = {"type": "object", "required": ["name"], "properties": {
    "gr": {
      "type": "array",
      "items": {
        "enum": [
          "GR®65",
          "GR®653",
          "GR®78",
          "GR®654"
        ],
        "type": "string"
      },
      "title": "GR®",
      "uniqueItems": True
    },
    "own": {
      "type": "string",
      "title": "Propriétaire(s)"
    },
    "logo": {
      "type": "string",
      "title": "Logo",
      "format": "data-url"
    },
    "distance": {
      "type": "number",
      "title": "Distance"
    },
    "travaux_a_realiser": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "annee",
          "description"
        ],
        "properties": {
          "annee": {
            "type": "string",
            "title": "Année"
          },
          "nature": {
            "enum": [
              "Mise en sécurité",
              "Stabilisation de l'emprise du chemin",
              "Sécurisation des abords"
            ],
            "type": "string",
            "title": "Nature"
          },
          "description": {
            "type": "string",
            "title": "Description"
          },
          "cout_financier": {
            "type": "number",
            "title": "Coût financier"
          },
          "maitre_ouvrage": {
            "type": "string",
            "title": "Maître d'ouvrage"
          },
          "maitrise_oeuvre": {
            "type": "string",
            "title": "Maîtrise d'oeuvre"
          }
        }
      },
      "title": "Travaux à réaliser"
    },
    "autres_donnees_frequentation": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "date": {
            "type": "string",
            "title": "Date",
            "format": "date"
          },
          "source": {
            "type": "string",
            "title": "Source"
          },
          "chiffres": {
            "type": "number",
            "title": "Chiffres"
          },
          "lieux_collecte": {
            "type": "string",
            "title": "Lieux de collecte"
          }
        }
      },
      "title": "Autres données de fréquentation"
    },
  }
}


class SchemaToModelSchemaTestCase(TestCase):
    def test_schema_to_schemamodel(self):
        self.maxDiff = None
        layer = Layer.objects.create(name='out')
        schema_to_schemamodel(layer, schema_complex)
        self.assertCountEqual(layer.generated_schema, test)
