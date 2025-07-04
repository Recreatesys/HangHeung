/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
  async onClickOrder(clickedOrder) {
    super.onClickOrder(clickedOrder);
    if (!clickedOrder || clickedOrder.uiState.locked) {
      var order = clickedOrder;
      console.log("clickedOrder", clickedOrder);
      
      if (order.name &&  this.pos.config.sh_pos_receipt_invoice) {
        let Orders = await this.pos.data.call("pos.order","search_read",[[["pos_reference", "=", order.name]]]);
        if (Orders && Orders.length > 0) {
          if (Orders[0] && Orders[0]["account_move"] &&this.pos.config.sh_pos_receipt_invoice) {
            var invoice_number = Orders[0]["account_move"][1].split(" ")[0];
            order["invoice_number"] = invoice_number;
          }
        }
      }
    } else {
      this._setOrder(clickedOrder);
    }
  },
});
