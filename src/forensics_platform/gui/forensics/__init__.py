"""
GUI Forensics package widgets.
"""

from forensics_platform.gui.forensics.case_manager_widget import CaseManagerWidget, NewCaseDialog
from forensics_platform.gui.forensics.evidence_manager_widget import EvidenceManagerWidget, RegisterEvidenceDialog
from forensics_platform.gui.forensics.audit_viewer_widget import AuditViewerWidget
from forensics_platform.gui.forensics.recovery_widget import RecoveryWidget

__all__ = [
    "CaseManagerWidget",
    "NewCaseDialog",
    "EvidenceManagerWidget",
    "RegisterEvidenceDialog",
    "AuditViewerWidget",
    "RecoveryWidget",
]
