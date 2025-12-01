from application.entities.base_entity import BaseEntity

class Subscription(BaseEntity):
    """Subscription entity"""
    
    TABLE_NAME = "Subscriptions"
    
    def __init__(self, subscription_id=None, unreg_user_id=None, plan_id=None,
                 start_date=None, end_date=None, status='active',
                 stripe_subscription_id=None, created_at=None):
        self.subscription_id = subscription_id
        self.unreg_user_id = unreg_user_id
        self.plan_id = plan_id
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.stripe_subscription_id = stripe_subscription_id
        self.created_at = created_at
    
    @classmethod
    def create_table(cls, app):
        """Create subscriptions table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            subscription_id INT PRIMARY KEY AUTO_INCREMENT,
            unreg_user_id INT NOT NULL,
            plan_id INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status ENUM('active', 'expired', 'cancelled', 'pending_payment') DEFAULT 'active',
            stripe_subscription_id VARCHAR(255) NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        cls.execute_query(app, query)