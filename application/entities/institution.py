from application.entities.base_entity import BaseEntity

class Institution(BaseEntity):
    """Institution entity"""
    
    TABLE_NAME = "Institutions"
    
    def __init__(self, institution_id=None, name=None, address=None, website=None,
                 subscription_id=None, is_active=True, created_at=None):
        self.institution_id = institution_id
        self.name = name
        self.address = address
        self.website = website
        self.subscription_id = subscription_id
        self.is_active = is_active
        self.created_at = created_at
    
    @classmethod
    def create_table(cls, app):
        """Create institutions table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            institution_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            website VARCHAR(255),
            subscription_id INT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_institution_subscription (subscription_id)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def create(cls, app, institution_data):
        """Create a new institution"""
        query = f"""
        INSERT INTO {cls.TABLE_NAME} (name, address, website, subscription_id, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            institution_data.get('name'),
            institution_data.get('address'),
            institution_data.get('website'),
            institution_data.get('subscription_id'),
            institution_data.get('is_active', True)
        )
        
        cursor = cls.get_db_connection(app)
        cursor.execute(query, params)
        institution_id = cursor.lastrowid
        cursor.close()
        cls.commit_changes(app)
        
        return institution_id
    
    @classmethod
    def get_by_id(cls, app, institution_id):
        """Get institution by ID"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE institution_id = %s"
        result = cls.execute_query(app, query, (institution_id,), fetch_one=True)
        
        if result:
            return cls.from_db_result(result)
        return None
    
    @classmethod
    def from_db_result(cls, db_result):
        """Create Institution object from database result"""
        return Institution(
            institution_id=db_result[0],
            name=db_result[1],
            address=db_result[2],
            website=db_result[3],
            subscription_id=db_result[4],
            is_active=bool(db_result[5]),
            created_at=db_result[6]
        )
    
    def to_dict(self):
        """Convert institution object to dictionary"""
        return {
            'institution_id': self.institution_id,
            'name': self.name,
            'address': self.address,
            'website': self.website,
            'subscription_id': self.subscription_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }