from application.entities.base_entity import BaseEntity


class UnregisteredUser(BaseEntity):
    """Entity representing registration applications (Unregistered_Users table)"""

    @classmethod
    def _get_db(cls):
        from flask import current_app
        return current_app.config.get('db')

    @property
    def db(self):
        return self._get_db()

    @classmethod
    def get_model(cls):
        db = cls._get_db()

        if not hasattr(cls, '_model_class'):

            class UnregisteredUserModel(db.Model, BaseEntity):
                __tablename__ = 'Unregistered_Users'

                unreg_user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                email = db.Column(db.String(255), nullable=False, unique=True)
                full_name = db.Column(db.String(100), nullable=False)
                institution_name = db.Column(db.String(255), nullable=False)
                institution_address = db.Column(db.Text)
                phone_number = db.Column(db.String(20))
                message = db.Column(db.Text)
                selected_plan_id = db.Column(db.Integer, db.ForeignKey('Subscription_Plans.plan_id'))
                status = db.Column(db.Enum('pending','approved','rejected'), default='pending')
                reviewed_by = db.Column(db.Integer, db.ForeignKey('Platform_Managers.platform_mgr_id'), nullable=True)
                reviewed_at = db.Column(db.DateTime, nullable=True)
                response_message = db.Column(db.Text, nullable=True)
                applied_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

                def __repr__(self):
                    return f"<UnregisteredUser {self.email} - {self.institution_name}>"

            cls._model_class = UnregisteredUserModel

        return cls._model_class

    @classmethod
    def get_by_email(cls, app, email):
        try:
            return cls.get_model().get_by_email(app, email)
        except Exception:
            return None

    @classmethod
    def from_db_result(cls, result_tuple):
        if not result_tuple:
            return None
        if hasattr(result_tuple, 'unreg_user_id'):
            return result_tuple

        # Map raw SQL tuple to model
        return cls.get_model()(
            unreg_user_id=result_tuple[0],
            email=result_tuple[1],
            full_name=result_tuple[2] if len(result_tuple) > 2 else None,
            institution_name=result_tuple[3] if len(result_tuple) > 3 else None,
            institution_address=result_tuple[4] if len(result_tuple) > 4 else None,
            phone_number=result_tuple[5] if len(result_tuple) > 5 else None,
            message=result_tuple[6] if len(result_tuple) > 6 else None,
            selected_plan_id=result_tuple[7] if len(result_tuple) > 7 else None,
            status=result_tuple[8] if len(result_tuple) > 8 else None,
            reviewed_by=result_tuple[9] if len(result_tuple) > 9 else None,
            reviewed_at=result_tuple[10] if len(result_tuple) > 10 else None,
            response_message=result_tuple[11] if len(result_tuple) > 11 else None,
            applied_at=result_tuple[12] if len(result_tuple) > 12 else None
        )

    @classmethod
    def create_table(cls, app):
        query = '''
        CREATE TABLE IF NOT EXISTS Unregistered_Users (
            unreg_user_id INT PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            institution_name VARCHAR(255) NOT NULL,
            institution_address TEXT,
            phone_number VARCHAR(20),
            message TEXT,
            selected_plan_id INT,
            status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            reviewed_by INT NULL,
            reviewed_at DATETIME NULL,
            response_message TEXT,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (selected_plan_id) REFERENCES Subscription_Plans(plan_id),
            FOREIGN KEY (reviewed_by) REFERENCES Platform_Managers(platform_mgr_id)
        )
        '''
        cls.execute_query(app, query)
