import copy
import math
import uuid

class trade:
    """An object representing a trade."""

    def __init__(self, date, type, shares, price, stop_loss = 0):
        self.id = uuid.uuid1()
        self.date = date

        self.type = type
        self.shares = float(shares)
        self.price  = float(price)
        self.stop_loss   = stop_loss
    
    def __str__(self):
        print("ID.     {0}".format(self.id))
        print("Date:   {0}".format(self.date))
        print("Type:   {0}".format(self.type))
        print("Price:  {0}".format(self.price))
        print("Shares: {0}".format(self.shares))
        print("Stop Loss:   {0}\n".format(self.stop_loss))

    def stop_hit(self, current_price):
        if self.type == 'buy':
            if current_price <= self.stop_loss:
                return True

        if self.type == 'sell':
            if current_price >= self.stop_loss:
                return True

class position:
    """A parent object representing a position."""

    def __init__(self, entry_date, shares, close_date = None):
        self.id            = uuid.uuid1()
        self.type          = "None"
        self.entry_date    = entry_date
        self.shares        = float(shares)
        self.close_date    = close_date
    
class long_position(position):
    """A child object representing a long position."""

    def __init__(self, entry_date, shares, close_date = None):
        super().__init__(entry_date, shares, close_date)
        self.type = 'long'

    def increase(self, shares):
        self.shares += shares

    def close(self, percent, current_price):
        shares = self.shares
        self.shares *= 1.0 - percent
        return shares * percent * current_price

class LocalAccount():
    """An object representing an exchange account."""

    def __init__(self, initial_capital, commision = 0, verbose = False):
        self.initial_capital = float(initial_capital)
        self.buying_power    = float(initial_capital)

        self.commision = commision
        self.verbose = verbose
        
        self.date            = None
        self.active_position = None

        self.equity          = []
        self.positions       = []
        self.trades          = []

    def buy(self, entry_capital, entry_price, stop_loss=0):
        entry_capital = float(entry_capital)
        
        if entry_capital <= 0: 
            raise ValueError("Error: Entry capital must be positive")       
        elif self.buying_power < entry_capital: 
            raise ValueError("Error: Not enough buying power to enter position")          
        else: 
            if self.commision > 0:
                shares = entry_capital / (entry_price + self.commision * entry_price)
            else:
                shares = entry_capital / entry_price

            self.buying_power -= entry_capital
            if self.active_position:
                self.active_position.increase(shares)
            
            else:
                self.active_position = long_position(self.date, shares)

            if self.verbose:
                print(100 * '-')
                print('{} | BUY ORDER'.format(self.date))
                print('{} | units = {} | price = {}'.format(self.date, shares, entry_price))
                print(100 * '-' + '\n')

            self.trades.append(trade(self.date,
                                    'buy',
                                    shares, 
                                    entry_price,
                                    stop_loss))

    def sell(self, percent, current_price, stop_loss = math.inf):
        if percent > 1 or percent < 0: 
            raise ValueError("Error: Percent must range between 0-1.")
        elif current_price < 0:
            raise ValueError("Error: Current price cannot be negative.")                
        else: 
            
            if self.active_position is not None:
                quantity = self.active_position.shares * percent
                self.trades.append(trade(self.date,
                                    'sell',
                                    quantity, 
                                    current_price,
                                    stop_loss))

                if self.commision > 0:
                    closing_position_price = self.active_position.close(percent, current_price)
                    self.buying_power += round((closing_position_price - closing_position_price * self.commision), 2)
                else:
                    self.buying_power += round(self.active_position.close(percent, current_price), 2)

                self.active_position.close_date = self.date
                if self.active_position.shares == 0:
                    self.positions.append(self.active_position)
                    self.active_position = None 

                if self.verbose:
                    print(100 * '-')
                    print('{} | SELL ORDER'.format(self.date))
                    print('{} | units = {} | price = {}'.format(self.date, quantity, current_price))
                    print(100 * '-' + '\n')

            else:
                raise ValueError("No active position! Cannot sell yet.")

    def show_positions(self):
        """Show all account positions.""" 
        for p in self.positions: p.show()

    def total_value(self, current_price):
        temporary = copy.deepcopy(self)
        temporary.verbose = False
        if self.active_position:
            temporary.sell(1.0, current_price)
        return round(temporary.buying_power, 2)