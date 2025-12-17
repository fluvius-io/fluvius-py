from fluvius.pdfgen import PdfAction, PdfPipeline, SignField, genpdf

# @TODO: Add output validation

"""
W9_PDF = 'fw9.pdf'
W9_SCHEMA = pypdftk.dump_data_fields(W9_PDF)
datas = {f['FieldName']: f['FieldName'] for f in W9_SCHEMA}
pypdftk.fill_form(W9_PDF, datas, 'fw9-annotated.pdf')
"""


def w9_data_mapper(data):
    yield "topmostSubform[0].Page1[0].f1_1[0]", data.get("name")
    yield "topmostSubform[0].Page1[0].f1_2[0]", data.get("business_name")
    yield "topmostSubform[0].Page1[0].Address[0].f1_7[0]", data.get("address")

    tax_classification = data.get("tax_classification") or 1
    yield f"topmostSubform[0].Page1[0].FederalClassification[0].c1_1[{tax_classification - 1}]", str(  # noqa: E501
        tax_classification
    )


def setup_complex_template(template_id, network_template=""):
    W9_PDF = "data/fw9.pdf"

    network_agreement = PdfAction(
        "fill-form",
        template=network_template,
        pages=33,
        sign_fields=[
            SignField(page=33, api_id="nw_signature_01"),
            SignField(page=33, api_id="nw_signature_02"),
        ],
    )

    w9_form = PdfAction(
        "fill-form",
        template=W9_PDF,
        data_mapper=w9_data_mapper,
        pages=6,
        sign_fields=SignField(page=1, api_id="w9_signature"),
    )
    concatenate = PdfAction("concat-pdftk")

    return PdfPipeline(
        [
            [w9_form, "data/sample-pdf/sample-no-content.pdf", network_agreement],
            concatenate,
        ],
        template_id=template_id,
    )


def test_complex_template():
    w9_data = {
        "name": "TEST ONBOARD Contract, LLC.",
        "business_name": "TEST W9 FORM, LLC.",
        "address": "123 Test Road",
        "tax_classification": 3,
    }

    setup_complex_template(
        "tpn_complex_form", "tmpl/template/TECQ_L20_202101_1/BASE/PPA.pdf"
    )
    result = genpdf("tpn_complex_form", w9_data)
    assert (
        result.sign_fields[0].page == 1
        and result.sign_fields[0].api_id == "w9_signature"
    )  # w9_form is the first element
    assert (
        result.sign_fields[1].page == 49
        and result.sign_fields[1].api_id == "nw_signature_01"
    )  # 6 (w9) + 10 (sample-no-content.pdf) + 33 (nw_signature_01)
    print(result)
