import xlsxwriter

from datetime import datetime
from fluvius.dmap.writer import config, logger
from fluvius.dmap.writer import register_writer, FileWriter

DEBUG_WRITER = config.DEBUG_WRITER


pallete = (
    ("#8dd3c7", "#80b1d3", "#d9d9d9"),
    ("#b3de69", "#bebada", "#bc80bd"),
    (
        "#b3de69",
        "#ccebc5",
        "#fdb462",
        "#ffffb3",
        "#fb8072",
        "#fccde5",
        "#ffed6f",
    ),
)


@register_writer('xlsx')
class ExcelWriter(FileWriter):
    file_extension = "xlsx"

    def write(self, data_profile):

        # output as 1 level header for viewing
        outfile = self.get_filepath(data_profile)

        workbook = xlsxwriter.Workbook(outfile)
        worksheet = workbook.add_worksheet()
        dt_fmt = workbook.add_format({"num_format": "mm/dd/yy"})

        field_map = data_profile.field_map
        index_map = data_profile.field_hdr

        self.check_unmapped_values(field_map, index_map)

        # if data_profile.debug_header is None:
        #     hdr_offset = self._write_full_debug_header(
        #         workbook, worksheet)
        # else:

        hdr_offset = self._write_fieldmap_header(
            workbook, worksheet, data_profile.headers)

        headers, stream = self.consume(data_profile)

        for row_idx, row in enumerate(stream):
            for data_id, col_value in enumerate(row):
                if isinstance(col_value, datetime):
                    worksheet.write_datetime(
                        row_idx + hdr_offset, data_id, col_value, dt_fmt
                    )
                if isinstance(col_value, str):
                    worksheet.write_string(
                        row_idx + hdr_offset, data_id, col_value
                    )
                else:
                    worksheet.write(row_idx + hdr_offset, data_id, col_value)
        workbook.close()
        DEBUG_WRITER and logger.info(
            "Excel output has been written to: %s", outfile
        )

    def _write_fieldmap_header(self, workbook, worksheet, header):
        fmHeaders = workbook.add_format(
            {"bold": 1, "align": "left", "bg_color": "#D9D9D9"}
        )

        for (idx, lbl) in enumerate(header):
            cell_fmt = fmHeaders
            worksheet.write(0, idx, lbl, cell_fmt)

        return 1  # header offset

    def _write_full_debug_header(self, workbook, worksheet, header):
        for row_idx, hdr_row in enumerate(header):
            fmHeaders = []
            fmCount = len(pallete[row_idx])
            # Add a bold format to use to highlight cells.
            for clr in pallete[row_idx]:
                fmHeaders.append(
                    workbook.add_format(
                        {
                            "bold": 1,
                            "align": "center_across"
                            if row_idx < 2
                            else "left",
                            "bg_color": clr,
                        }
                    )
                )

            for idx, (lbl, cell_width, cell_idx, _) in enumerate(hdr_row):
                fm = fmHeaders[idx % fmCount]
                if cell_width > 1:
                    worksheet.merge_range(
                        row_idx,
                        cell_idx,
                        row_idx,
                        cell_idx + cell_width - 1,
                        lbl,
                        fm,
                    )
                else:
                    worksheet.write(row_idx, cell_idx, lbl, fm)
        return 3  # header offset

    def output_repeated_value(self, field_map, index_map):
        logger.warn("Field map: %s", field_map)
        logger.warn("Index map: %s", index_map)

        # exist_on_fieldmap = []

        # for k, v in field_map.items():
        #     for index, _ in v:
        #         exist_on_fieldmap.append(index)

        # logger.warn("Field to look into:")
        # for key, value in index_map.items():
        #     if key not in exist_on_fieldmap:
        #         logger.warn(value)
        # logger.warn("----------------------")

    def check_unmapped_values(self, field_map, index_map):
        if len(field_map) == len(index_map):
            return

        logger.warn(
            "The mapping contain repeated"
            " selector, please review and make sure they are unique."
        )
        fieldmap_idx = []
        for _, v in field_map.items():
            for i in list(v):
                _, idx, _, _ = i
                fieldmap_idx.append(idx)
        for index_key in index_map:
            if index_key not in fieldmap_idx:
                logger.warn(index_key)
