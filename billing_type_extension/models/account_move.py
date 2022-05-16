from odoo import fields, models, api


class AccountMoveLineInherit(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        # print('\n\nCalculated price for invoice2 :',self.move_id.billing, price_unit, quantity, discount, currency, product, partner, taxes,
        #       self, move_type)
        res = {}
        # added for resolving error
        if self.move_id.invoice_origin:
            so = self.env['sale.order'].sudo().search([('name', '=', self.move_id.invoice_origin)])
            if so:
                for line in so.order_line:
                    if product.id == line.product_id.id:
                        price_unit = line.price_unit
                    # price_unit = so.order_line.price_unit
        # price_unit = self.move_id.
        # Compute 'price_subtotal'.
        if self.move_id.billing == 'normal':
            no_of_users = self.move_id.no_of_users
            print("new no of users\n", no_of_users)
        else:
            no_of_users = 1
            print("else new no of users\n", no_of_users)
        payment_term = self.move_id.invoice_term_id
        print("payment termsss\n", payment_term)
        months = 1
        if payment_term:
            if payment_term.name == 'Yearly':
                months = 12
        print("months \n", months)
        # quantity =
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        print(quantity, line_discount_price_unit, no_of_users, months, discount)
        subtotal = quantity * line_discount_price_unit * no_of_users * months
        print("subtotal \n\n", subtotal)
        # tots = quantity * line_discount_price_unit * no_of_users * months
        # Compute 'price_total'.

        if taxes:
            no_of_users = no_of_users * months
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner,
                                                                                      is_refund=move_type in (
                                                                                          'out_refund', 'in_refund'),
                                                                                      users=no_of_users)
            total = taxes_res['total_excluded']
            tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            res['price_subtotal'] = total
            res['price_total'] = total + tax_amount
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        # print(" res : ", res)
        return res
