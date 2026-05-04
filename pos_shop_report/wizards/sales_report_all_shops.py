from collections import defaultdict
from datetime import date, datetime
import base64
import io

import xlsxwriter

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SalesReportAllShopsWizard(models.TransientModel):
    _name = 'sales.report.all.shops.wizard'
    _description = 'Sales Report All Shops Wizard'

    def _default_start_date(self):
        return date.today().replace(day=1)

    file_data = fields.Binary('Excel File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)
    start_date = fields.Date('Start Date', default=_default_start_date, required=True)
    end_date = fields.Date('End Date', default=fields.Date.context_today, required=True)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for w in self:
            if w.start_date and w.end_date and w.end_date < w.start_date:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _aggregate_all_shops_data(self):
        self.ensure_one()
        shops = self.env['pos.config'].search([], order='name')
        if not shops:
            raise ValidationError("No POS shops configured.")

        coupon_program_types = ('coupons', 'gift_card', 'ewallet')

        base_domain = [('state', 'in', ['paid', 'done', 'invoiced'])]
        cancel_domain = [('state', 'in', ['cancel'])]
        if self.start_date:
            base_domain.append(('date_order', '>=', self.start_date))
            cancel_domain.append(('date_order', '>=', self.start_date))
        if self.end_date:
            base_domain.append(('date_order', '<=', self.end_date))
            cancel_domain.append(('date_order', '<=', self.end_date))

        payment_amount = defaultdict(lambda: defaultdict(float))
        payment_txn = defaultdict(lambda: defaultdict(int))
        void_amount = defaultdict(lambda: defaultdict(float))
        void_qty = defaultdict(lambda: defaultdict(float))
        coupon_amount = defaultdict(lambda: defaultdict(float))
        coupon_qty = defaultdict(lambda: defaultdict(int))
        discount_amount = defaultdict(lambda: defaultdict(float))
        discount_qty = defaultdict(lambda: defaultdict(int))

        shop_totals = {}

        for shop in shops:
            d = base_domain + [('config_id', '=', shop.id)]
            cd = cancel_domain + [('config_id', '=', shop.id)]
            orders = self.env['pos.order'].search(d)
            cancel_orders = self.env['pos.order'].search(cd)

            order_total = sum(orders.mapped('amount_total'))
            cancel_order_total = sum(cancel_orders.mapped('amount_total'))
            cancel_qty_shop = sum(line.qty for o in cancel_orders for line in o.lines)

            net_amount = 0.0
            net_txn = 0
            for payment in orders.mapped('payment_ids'):
                method = payment.payment_method_id.name or 'Unknown'
                payment_amount[method][shop.id] += payment.amount
                payment_txn[method][shop.id] += 1
                net_amount += payment.amount
                net_txn += 1

            for order in cancel_orders:
                order_qty = sum(l.qty for l in order.lines)
                payments = order.payment_ids
                if not payments:
                    void_qty['(No Payment)'][shop.id] += order_qty
                    continue
                n = len(payments)
                for p in payments:
                    method = p.payment_method_id.name or 'Unknown'
                    void_amount[method][shop.id] += p.amount
                    void_qty[method][shop.id] += order_qty / n

            for line in orders.mapped('lines'):
                if not line.is_reward_line or not line.reward_id:
                    continue
                program = line.reward_id.program_id
                name = program.name or 'Unknown'
                if program.program_type in coupon_program_types:
                    coupon_amount[name][shop.id] += abs(line.price_subtotal_incl)
                    coupon_qty[name][shop.id] += 1
                else:
                    discount_amount[name][shop.id] += abs(line.price_subtotal_incl)
                    discount_qty[name][shop.id] += 1

            shop_totals[shop.id] = {
                'order_total': order_total,
                'cancel_order_total': cancel_order_total,
                'cancel_qty': cancel_qty_shop,
                'net_amount': net_amount,
                'net_txn': net_txn,
            }

        def to_section(amount_map, qty_map):
            keys = sorted(set(list(amount_map.keys()) + list(qty_map.keys())),
                          key=lambda k: (k or '').lower())
            amount_rows = []
            qty_rows = []
            amount_col_totals = [0.0] * len(shops)
            qty_col_totals = [0.0] * len(shops)
            for k in keys:
                a_cells = [amount_map.get(k, {}).get(s.id, 0.0) for s in shops]
                q_cells = [qty_map.get(k, {}).get(s.id, 0) for s in shops]
                amount_rows.append({'label': k, 'cells': a_cells, 'subtotal': sum(a_cells)})
                qty_rows.append({'label': k, 'cells': q_cells, 'subtotal': sum(q_cells)})
                for i in range(len(shops)):
                    amount_col_totals[i] += a_cells[i]
                    qty_col_totals[i] += q_cells[i]
            return {
                'amount_rows': amount_rows,
                'amount_col_totals': amount_col_totals,
                'amount_grand': sum(amount_col_totals),
                'qty_rows': qty_rows,
                'qty_col_totals': qty_col_totals,
                'qty_grand': sum(qty_col_totals),
            }

        payment = to_section(payment_amount, payment_txn)
        void = to_section(void_amount, void_qty)
        coupon = to_section(coupon_amount, coupon_qty)
        discount = to_section(discount_amount, discount_qty)

        # Hoist the "Cash - <shop>" rows to the TOP of the payment-method
        # table and append a "Cash" subtotal row right under them, so the
        # grouped block appears above the rest of the payment methods
        # (e.g. above the AE row). Same treatment for amount and qty.
        def hoist_cash_with_subtotal(rows):
            cash_rows = [r for r in rows if (r['label'] or '').startswith('Cash - ')]
            other_rows = [r for r in rows if not (r['label'] or '').startswith('Cash - ')]
            if not cash_rows:
                return rows
            block = list(cash_rows)
            if len(cash_rows) > 1:
                n_cells = len(cash_rows[0]['cells'])
                cells = [sum(r['cells'][i] for r in cash_rows) for i in range(n_cells)]
                block.append({
                    'label': 'Cash',
                    'cells': cells,
                    'subtotal': sum(cells),
                    'is_subtotal': True,
                })
            return block + other_rows

        payment['amount_rows'] = hoist_cash_with_subtotal(payment['amount_rows'])
        payment['qty_rows'] = hoist_cash_with_subtotal(payment['qty_rows'])

        header_metrics = [
            {
                'label': '總計($)',
                'cells': [shop_totals[s.id]['order_total'] for s in shops],
                'subtotal': sum(shop_totals[s.id]['order_total'] for s in shops),
                'is_money': True,
            },
            {
                'label': '交易數量',
                'cells': [shop_totals[s.id]['net_txn'] for s in shops],
                'subtotal': sum(shop_totals[s.id]['net_txn'] for s in shops),
                'is_money': False,
            },
        ]

        return {
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else '',
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else '',
            'shops': [{'id': s.id, 'name': s.name} for s in shops],
            'header_metrics': header_metrics,
            'payment': payment,
            'void': void,
            'coupon': coupon,
            'discount': discount,
        }

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------
    def action_generate_excel(self):
        self.ensure_one()
        d = self._aggregate_all_shops_data()
        shops = d['shops']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Sales Report All Shops")

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
        })
        label_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'left',
        })
        money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        int_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})
        total_money_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'border': 1, 'align': 'right',
            'bold': True, 'bg_color': '#FFF2CC',
        })
        total_int_fmt = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'align': 'right',
            'bold': True, 'bg_color': '#FFF2CC',
        })
        plain_fmt = workbook.add_format({'border': 1, 'align': 'left'})
        big_title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        section_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#BDD7EE'})

        # column widths
        sheet.set_column(0, 0, 32)
        sheet.set_column(1, len(shops), 14)
        sheet.set_column(len(shops) + 1, len(shops) + 1, 16)

        row = 0
        sheet.write(row, 0, "Sales Report - All Shops", big_title_fmt)
        row += 1
        sheet.write(row, 0, f"日期: {d['start_date']} ~ {d['end_date']}")
        row += 2

        def write_matrix(title, rows_data, value_fmt, total_fmt, label_col_title):
            nonlocal row
            sheet.merge_range(row, 0, row, len(shops) + 1, title, section_fmt)
            row += 1
            sheet.write(row, 0, label_col_title, header_fmt)
            for i, s in enumerate(shops):
                sheet.write(row, 1 + i, s['name'], header_fmt)
            sheet.write(row, len(shops) + 1, "Subtotal", header_fmt)
            row += 1
            col_totals = [0] * len(shops)
            grand = 0
            for r in rows_data:
                row_label_fmt = total_fmt if r.get('is_subtotal') else label_fmt
                row_value_fmt = total_fmt if r.get('is_subtotal') else value_fmt
                sheet.write(row, 0, r['label'] or '', row_label_fmt)
                for i, val in enumerate(r['cells']):
                    sheet.write_number(row, 1 + i, val or 0, row_value_fmt)
                    if not r.get('is_subtotal'):
                        col_totals[i] += val or 0
                sheet.write_number(row, len(shops) + 1, r['subtotal'] or 0, total_fmt)
                if not r.get('is_subtotal'):
                    grand += r['subtotal'] or 0
                row += 1
            # 總計 row
            sheet.write(row, 0, "總計", label_fmt)
            for i, t in enumerate(col_totals):
                sheet.write_number(row, 1 + i, t, total_fmt)
            sheet.write_number(row, len(shops) + 1, grand, total_fmt)
            row += 2

        # Header summary
        sheet.merge_range(row, 0, row, len(shops) + 1, "Header Summary", section_fmt)
        row += 1
        sheet.write(row, 0, "Metric", header_fmt)
        for i, s in enumerate(shops):
            sheet.write(row, 1 + i, s['name'], header_fmt)
        sheet.write(row, len(shops) + 1, "Subtotal", header_fmt)
        row += 1
        for m in d['header_metrics']:
            fmt = total_money_fmt if m['is_money'] else total_int_fmt
            cell_fmt = money_fmt if m['is_money'] else int_fmt
            sheet.write(row, 0, m['label'], label_fmt)
            for i, val in enumerate(m['cells']):
                sheet.write_number(row, 1 + i, val or 0, cell_fmt)
            sheet.write_number(row, len(shops) + 1, m['subtotal'] or 0, fmt)
            row += 1
        row += 1

        write_matrix("支付方式 - Amount", d['payment']['amount_rows'], money_fmt, total_money_fmt, "支付方式")
        write_matrix("支付方式 - Transactions", d['payment']['qty_rows'], int_fmt, total_int_fmt, "支付方式")
        write_matrix("Void單 - Amount", d['void']['amount_rows'], money_fmt, total_money_fmt, "Payment Method")
        write_matrix("Void單 - Quantity", d['void']['qty_rows'], money_fmt, total_money_fmt, "Payment Method")
        write_matrix("咭類兌換 - Amount Redeemed", d['coupon']['amount_rows'], money_fmt, total_money_fmt, "Coupon")
        write_matrix("咭類兌換 - Quantity Redeemed", d['coupon']['qty_rows'], int_fmt, total_int_fmt, "Coupon")
        write_matrix("Discount - Amount", d['discount']['amount_rows'], money_fmt, total_money_fmt, "Discount")
        write_matrix("Discount - Quantity", d['discount']['qty_rows'], int_fmt, total_int_fmt, "Discount")

        workbook.close()
        output.seek(0)
        excel_data = output.read()

        filename = f"Sales Report All Shops {datetime.today().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': filename,
        })
        self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def action_generate_pdf(self):
        self.ensure_one()
        # Pre-validate by computing once
        self._aggregate_all_shops_data()
        return self.env.ref('pos_shop_report.action_sales_report_all_shops_pdf').report_action(self)
