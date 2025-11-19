from odoo import models, fields

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def confirm_coupon_programs(self, coupon_data):
        """Extend base to mark coupon as redeemed when used."""
        result = super().confirm_coupon_programs(coupon_data)

        
        old_to_new_map = {cu['old_id']: cu['id'] for cu in result.get('coupon_updates', [])}
        points_map = {cu['id']: cu['points'] for cu in result.get('coupon_updates', [])}

       
        all_coupon_ids = set(points_map.keys()).union(
            [int(cid) for cid in coupon_data.keys() if int(cid) > 0]
        )

        coupons = self.env['loyalty.card'].browse(all_coupon_ids)

        for coupon in coupons:
            points = points_map.get(coupon.id) or coupon_data.get(str(coupon.id), {}).get('points', 0)

            if points <= 0 and coupon.status != 'redeemed' and int(coupon.points_display[0]) == 0:
                coupon.write({
                    'status': 'redeemed',
                    'redeemed_datetime': fields.Datetime.now(),
                })

        return result
