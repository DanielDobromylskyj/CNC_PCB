

class ValueParser:
    def __init__(self, leading_zeros, absolute, before_decimal, after_decimal, unit="MM"):
        self.leading_zeros = leading_zeros
        self.absolute = absolute

        self.before_decimal = before_decimal
        self.after_decimal = after_decimal

        self.unit = unit

        self.last = 0


    def parse_value(self, value: str):
        if self.leading_zeros:
            stripped = value.lstrip('0')
            value = ("0" * ((self.before_decimal+self.after_decimal) - len(stripped))) + stripped
        else:
            stripped = value.rstrip('0')
            value = stripped + ("0" * ((self.before_decimal + self.after_decimal) - len(stripped)))

        parsed_value = int(value) / (10 * self.after_decimal)

        if self.unit == "IN":
            parsed_value = parsed_value * 25.4  # convert from inch to mm, cos bri'ish

        if self.absolute:
            return parsed_value

        else:
            self.last += parsed_value
            return self.last



