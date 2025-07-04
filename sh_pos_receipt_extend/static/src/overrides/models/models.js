/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { A3OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a3_receipt/a3_receipt";
import { A4OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a4_receipt/a4_receipt";
import { A5OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a5_receipt/a5_receipt";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(PosOrderline.prototype, {
  getDisplayData() {
    var res = super.getDisplayData()
    res['default_code'] = this.order_id.finalized && this.config.sh_enable_internal_ref ? this.get_product().default_code : false;
    return res
  }
});

patch(Orderline, {
  props: {
      ...Orderline.props,
      line: {
          ...Orderline.props.line,
          shape: {
              ...Orderline.props.line.shape,
              default_code: { type: [String, Boolean], optional: true },
          },

      },
  },
});

patch(PosStore.prototype, {
  getReceiptHeaderData(order){
    const result = super.getReceiptHeaderData(...arguments);
    result["invoice_number"]= order.invoice_number
    result["pos_recept_name"]= order.pos_recept_name    
    if(order.partner_id){
      result["partner"]= order.partner_id
      
    }
    return result
  },
  async A3printReceipt(){
    const isPrinted = await this.printer.print(
      A3OrderReceipt,
      {
          data: this.orderExportForPrinting(this.get_order()),
          formatCurrency: this.env.utils.formatCurrency,
      },
      { webPrintFallback: true }
  );
  if (isPrinted) {
      this.get_order()._printed = true;
  }
  },
  async A4printReceipt(){
    const isPrinted = await this.printer.print(
      A4OrderReceipt,
      {
          data: this.orderExportForPrinting(this.get_order()),
          formatCurrency: this.env.utils.formatCurrency,
      },
      { webPrintFallback: true }
  );
  if (isPrinted) {
      this.get_order()._printed = true;
  }
  },
  async A5printReceipt(){
    const isPrinted = await this.printer.print(
      A5OrderReceipt,
      {
          data: this.orderExportForPrinting(this.get_order()),
          formatCurrency: this.env.utils.formatCurrency,
      },
      { webPrintFallback: true }
  );
  if (isPrinted) {
      this.get_order()._printed = true;
  }
  }
})