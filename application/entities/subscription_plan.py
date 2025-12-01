from application.entities.base_entity import BaseEntity
import json

class SubscriptionPlan(BaseEntity):
    """Subscription Plan entity"""
    
    TABLE_NAME = "Subscription_Plans"
    
    def __init__(self, plan_id=None, plan_name=None, description=None,
                 price_per_cycle=None, billing_cycle=None, max_students=None,
                 max_courses=None, max_lecturers=None, features=None,
                 is_active=True, created_at=None):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.description = description
        self.price_per_cycle = price_per_cycle
        self.billing_cycle = billing_cycle
        self.max_students = max_students
        self.max_courses = max_courses
        self.max_lecturers = max_lecturers
        self.features = features if isinstance(features, dict) else json.loads(features) if features else {}
        self.is_active = is_active
        self.created_at = created_at
    
    @classmethod
    def create_table(cls, app):
        """Create subscription plans table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            plan_id INT PRIMARY KEY AUTO_INCREMENT,
            plan_name VARCHAR(100) NOT NULL,
            description TEXT,
            price_per_cycle DECIMAL(10,2) NOT NULL,
            billing_cycle ENUM('monthly', 'quarterly', 'annual') NOT NULL,
            max_students INT NOT NULL,
            max_courses INT NOT NULL,
            max_lecturers INT NOT NULL,
            features JSON,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        cls.execute_query(app, query)