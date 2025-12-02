from fluvius.pdfgen import PdfAction, PdfPipeline, genpdf

"""
W9_PDF = 'fw9.pdf'
W9_SCHEMA = pypdftk.dump_data_fields(W9_PDF)
datas = {f['FieldName']: f['FieldName'] for f in W9_SCHEMA}
pypdftk.fill_form(W9_PDF, datas, 'fw9-annotated.pdf')
"""


def setup_w9_template(template_id):
    W9_PDF = "data/fw9.pdf"

    def w9_data_mapper(data):
        yield "topmostSubform[0].Page1[0].f1_1[0]", data.get("name")
        yield "topmostSubform[0].Page1[0].f1_2[0]", data.get("business_name")
        yield "topmostSubform[0].Page1[0].Address[0].f1_7[0]", data.get("address")

        tax_classification = data.get("tax_classification") or 1
        yield f"topmostSubform[0].Page1[0].FederalClassification[0].c1_1[{tax_classification - 1}]", str(  # noqa: E501
            tax_classification
        )

    w9_form = PdfAction("fill-form", template=W9_PDF, data_mapper=w9_data_mapper)
    return PdfPipeline([w9_form], template_id=template_id)


def test_form_filling():
    w9_data = {
        "name": "Onboarding_Contract, LLC.",
        "business_name": "TEST W9 FORM, LLC.",
        "address": "123 Test Road",
        "tax_classification": 3,
    }

    setup_w9_template("w9_form")
    result = genpdf("w9_form", w9_data)
    print(result)


""" Sample data

W9_SCHEMA = [{'FieldFlags': '8388608',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].f1_1[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].f1_2[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[0]',
  'FieldStateOption': ['1', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[1]',
  'FieldStateOption': ['2', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[2]',
  'FieldStateOption': ['3', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[3]',
  'FieldStateOption': ['4', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[4]',
  'FieldStateOption': ['5', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[5]',
  'FieldStateOption': ['6', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '0',
  'FieldJustification': 'Center',
  'FieldMaxLength': '1',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].f1_3[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '0',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].c1_1[6]',
  'FieldStateOption': ['7', 'Off'],
  'FieldType': 'Button',
  'FieldValue': 'Off'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Center',
  'FieldName': 'topmostSubform[0].Page1[0].FederalClassification[0].f1_4[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Center',
  'FieldName': 'topmostSubform[0].Page1[0].Exemptions[0].f1_5[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Center',
  'FieldName': 'topmostSubform[0].Page1[0].Exemptions[0].f1_6[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].Address[0].f1_7[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].Address[0].f1_8[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8392704',
  'FieldJustification': 'Left',
  'FieldName': 'topmostSubform[0].Page1[0].f1_9[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '8388608',
  'FieldJustification': 'Center',
  'FieldName': 'topmostSubform[0].Page1[0].f1_10[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '25165824',
  'FieldJustification': 'Left',
  'FieldMaxLength': '3',
  'FieldName': 'topmostSubform[0].Page1[0].SSN[0].f1_11[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '25165824',
  'FieldJustification': 'Left',
  'FieldMaxLength': '2',
  'FieldName': 'topmostSubform[0].Page1[0].SSN[0].f1_12[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '25165824',
  'FieldJustification': 'Left',
  'FieldMaxLength': '4',
  'FieldName': 'topmostSubform[0].Page1[0].SSN[0].f1_13[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '25165824',
  'FieldJustification': 'Left',
  'FieldMaxLength': '2',
  'FieldName': 'topmostSubform[0].Page1[0].EmployerID[0].f1_14[0]',
  'FieldType': 'Text'},
 {'FieldFlags': '25165824',
  'FieldJustification': 'Left',
  'FieldMaxLength': '7',
  'FieldName': 'topmostSubform[0].Page1[0].EmployerID[0].f1_15[0]',
  'FieldType': 'Text'}]
"""
