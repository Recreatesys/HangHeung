/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
// import { ReprintReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/reprint_receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { A3OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a3_receipt/a3_receipt";
import { A4OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a4_receipt/a4_receipt";
import { A5OrderReceipt } from "@sh_pos_receipt_extend/app/receipt/a5_receipt/a5_receipt";

Object.assign(ReceiptScreen.components, { A3OrderReceipt , A4OrderReceipt , A5OrderReceipt});
// Object.assign(ReprintReceiptScreen.components, { A3OrderReceipt , A4OrderReceipt , A5OrderReceipt});

// patch(ReprintReceiptScreen.prototype, {
//   async printA3Receipt() {
//     this.printer.print(
//       A3OrderReceipt,
//       {
//           data: this.pos.orderExportForPrinting(this.props.order),
//           formatCurrency: this.env.utils.formatCurrency,
//       },
//       { webPrintFallback: true }
//   );
//   },
//   async printA4Receipt() {
//     this.printer.print(
//       A4OrderReceipt,
//       {
//           data: this.pos.orderExportForPrinting(this.props.order),
//           formatCurrency: this.env.utils.formatCurrency,
//       },
//       { webPrintFallback: true }
//   );
//   },

//   async printA5Receipt() {
//     this.printer.print(
//       A5OrderReceipt,
//       {
//           data: this.pos.orderExportForPrinting(this.props.order),
//           formatCurrency: this.env.utils.formatCurrency,
//       },
//       { webPrintFallback: true }
//   );
//   },
// })

patch(ReceiptScreen.prototype, {

  setup() {
    super.setup();
    console.log("comaponnet  ", ReceiptScreen.components);
    
    this.receipt_type = "standard";
    this.pos.receipt_type = false;
    this.orm = useService("orm");
    this.is_not_standard_size = false;
    var config = this.pos.config;
    if (config.sh_enable_a3_receipt ||config.sh_enable_a4_receipt ||config.sh_enable_a5_receipt) {
      if (config.sh_default_receipt) {
        this.receipt_type = config.sh_default_receipt;
      }
    }else if(!config.sh_enable_a3_receipt || !config.sh_enable_a4_receipt || !config.sh_enable_a5_receipt){
      if (config.sh_default_receipt) {
        this.receipt_type = config.sh_default_receipt;
      }
    }
    this.amount_in_words();
    this.get_order_details();
    var self = this;
    var order = self.pos.get_order();
    // onMounted(this.onMounted);
  },
  // onMounted() {
  //   if(this.receipt_type && this.receipt_type != 'standard' && $('.pos-receipt')){
  //     for (let each_receipt of $('.pos-receipt')) {
  //       if(!$(each_receipt).hasClass('a3_size_receipt') && !$(each_receipt).hasClass('a4_size_receipt') && !$(each_receipt).hasClass('a5_size_receipt')){
  //         $(each_receipt).addClass('sh_standard_receipt')
  //       }
  //     }
  //   }
  // },
  async get_order_details() {
    let order = this.pos.get_order();
    const domain = [
      ["pos_reference", "=", order.pos_reference]
  ];
    let Orders = await this.orm.searchRead(
      "pos.order",
      [["pos_reference", "=", order.pos_reference]]
  );
    if (order.is_to_invoice() && this.pos.config.sh_pos_receipt_invoice) {
      if (Orders) {
        if (
          Orders.length > 0 &&
          Orders[0]["account_move"] &&
          Orders[0]["account_move"][1]
        ) {
          var invoice_number = Orders[0]["account_move"][1].split(" ")[0];
          order["invoice_number"] = invoice_number;
        }
        this.render();
      }
    }
  },

  async amount_in_words() {
    var total_with_tax_in_words = "";
    var self = this;
    let cur = await self.orm.call("res.currency", "amount_to_text", [
      self.pos.currency.id,
      self.pos.get_order().get_total_with_tax(),
    ]);
    if (cur) {
      total_with_tax_in_words = cur;
    }

    self.pos.get_order().total_with_tax_in_words = total_with_tax_in_words;
  },

  async printA3Receipt() {
    this.pos.A3printReceipt();
  },
  async printA4Receipt() {
    this.pos.A4printReceipt();
  },

  async printA5Receipt() {
    this.pos.A5printReceipt();
  },


});
