"""
Database module for appointment management in the Eonix insurance platform.
"""
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

# Configure logger
logger = logging.getLogger(__name__)

class AppointmentDatabase:
    """
    Handles storage and retrieval of appointment data.
    In a production environment, this would connect to a real database.
    """
    
    def __init__(self):
        """Initialize the appointment database."""
        self.data_dir = os.path.join(os.path.dirname(__file__), '../data')
        self.appointments_file = os.path.join(self.data_dir, 'appointments.json')
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create empty appointments file if it doesn't exist
        if not os.path.exists(self.appointments_file):
            with open(self.appointments_file, 'w') as f:
                json.dump([], f)
        
        logger.info("Appointment database initialized")
    
    def get_appointments(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all appointments, optionally filtered by date range.
        
        Args:
            days: Number of days to include from today, or None for all
            
        Returns:
            List of appointment objects
        """
        try:
            with open(self.appointments_file, 'r') as f:
                appointments = json.load(f)
            
            # If days is specified, filter by date range
            if days is not None:
                today = datetime.now().date()
                end_date = today + timedelta(days=days)
                
                filtered_appointments = []
                for appointment in appointments:
                    try:
                        appointment_date = datetime.strptime(appointment.get('date', ''), '%Y-%m-%d').date()
                        if today <= appointment_date <= end_date:
                            filtered_appointments.append(appointment)
                    except ValueError:
                        # Skip appointments with invalid dates
                        pass
                
                return filtered_appointments
            
            return appointments
            
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return []
    
    def get_appointment_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an appointment by ID.
        
        Args:
            appointment_id: ID of the appointment
            
        Returns:
            Appointment object or None if not found
        """
        try:
            with open(self.appointments_file, 'r') as f:
                appointments = json.load(f)
            
            for appointment in appointments:
                if appointment.get('id') == appointment_id:
                    return appointment
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting appointment by ID: {e}")
            return None
    
    def add_appointment(self, appointment_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new appointment.
        
        Args:
            appointment_data: Appointment data
            
        Returns:
            ID of the new appointment, or None if error
        """
        try:
            with open(self.appointments_file, 'r') as f:
                appointments = json.load(f)
            
            # Generate an ID if not provided
            if 'id' not in appointment_data:
                appointment_data['id'] = str(uuid.uuid4())
            
            # Add created_at timestamp
            appointment_data['created_at'] = datetime.now().isoformat()
            
            # Add to list
            appointments.append(appointment_data)
            
            # Save back to file
            with open(self.appointments_file, 'w') as f:
                json.dump(appointments, f, indent=2)
            
            logger.info(f"Added appointment with ID {appointment_data['id']}")
            return appointment_data['id']
            
        except Exception as e:
            logger.error(f"Error adding appointment: {e}")
            return None
    
    def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> bool:
        """
        Update an existing appointment.
        
        Args:
            appointment_id: ID of the appointment to update
            appointment_data: New appointment data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.appointments_file, 'r') as f:
                appointments = json.load(f)
            
            # Find and update the appointment
            for i, appointment in enumerate(appointments):
                if appointment.get('id') == appointment_id:
                    # Update fields while preserving the ID
                    appointment_data['id'] = appointment_id
                    appointment_data['updated_at'] = datetime.now().isoformat()
                    appointments[i] = {**appointment, **appointment_data}
                    
                    # Save back to file
                    with open(self.appointments_file, 'w') as f:
                        json.dump(appointments, f, indent=2)
                    
                    logger.info(f"Updated appointment with ID {appointment_id}")
                    return True
            
            logger.warning(f"Appointment with ID {appointment_id} not found for update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            return False
    
    def delete_appointment(self, appointment_id: str) -> bool:
        """
        Delete an appointment.
        
        Args:
            appointment_id: ID of the appointment to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.appointments_file, 'r') as f:
                appointments = json.load(f)
            
            # Find and remove the appointment
            initial_count = len(appointments)
            appointments = [a for a in appointments if a.get('id') != appointment_id]
            
            if len(appointments) < initial_count:
                # Save back to file
                with open(self.appointments_file, 'w') as f:
                    json.dump(appointments, f, indent=2)
                
                logger.info(f"Deleted appointment with ID {appointment_id}")
                return True
            
            logger.warning(f"Appointment with ID {appointment_id} not found for deletion")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting appointment: {e}")
            return False 