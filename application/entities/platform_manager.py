from application.entities.base_entity import BaseEntity

class PlatformManager(BaseEntity):
    """Platform Manager entity"""
    
    TABLE_NAME = "Platform_Managers"
    
    def __init__(self, platform_mgr_id=None, email=None, password_hash=None,
                 full_name=None, created_at=None):
        self.platform_mgr_id = platform_mgr_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.created_at = created_at
    
    @classmethod
    def create_table(cls, app):
        """Create platform managers table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            platform_mgr_id INT PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        cls.execute_query(app, query)