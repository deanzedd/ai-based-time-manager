import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple

# FIle này chứa:
# class Task:
#     


# --- Enum và Type Hints ---

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Task:
    def __init__(self,
                 id: int,
                 description: str,
                 duration_minutes: int,
                 priority: Priority,
                 due_date: Optional[datetime.datetime] = None,
                 preferred_time: Optional[str] = None, # Ví dụ: "morning", "afternoon", "evening"
                 energy_level: Optional[str] = None, # Ví dụ: "high", "medium", "low"
                 project_id: Optional[str] = None,
                 scheduled_start: Optional[datetime.datetime] = None,
                 scheduled_end: Optional[datetime.datetime] = None): 
        self.id = id
        self.description = description
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.due_date = due_date
        self.preferred_time = preferred_time
        self.energy_level = energy_level
        self.project_id = project_id
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end

    def __repr__(self) -> str:
        status = "Scheduled" if self.scheduled_start else "Pending"
        return (f"Task(id={self.id}, desc='{self.description}', prio={self.priority.name}, "
                f"duration={self.duration_minutes}min, status='{status}')")

class TimeSlot:
    def __init__(self, start: datetime.datetime, end: datetime.datetime):
        self.start = start
        self.end = end
        self.duration_minutes = int((end - start).total_seconds() / 60)

    def __repr__(self) -> str:
        return f"TimeSlot(start='{self.start.strftime('%H:%M')}', end='{self.end.strftime('%H:%M')}', duration={self.duration_minutes}min)"

class SlotScore:
    def __init__(self, total: float, factors: Dict[str, float]):
        self.total = total
        self.factors = factors

    def __repr__(self) -> str:
        factor_str = ", ".join([f"{key}={value:.2f}" for key, value in self.factors.items()])
        return f"SlotScore(total={self.total:.2f}, factors=[{factor_str}])"


# --- Scoring Logic  ---
# tính điểm cho slot cho từng việc dựa trên các factors với weights tương ứng

class SlotScorer:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.scheduled_tasks_by_project: Dict[str, List[Task]] = {} # Để xử lý project proximity

    def update_scheduled_tasks_for_projects(self, tasks: List[Task]):
        # Giả định mỗi task có thể có 'project_id' nếu cần
        self.scheduled_tasks_by_project.clear()
        for task in tasks:
            project_id = getattr(task, 'project_id', 'default_project') # Lấy project_id nếu có
            if project_id not in self.scheduled_tasks_by_project:
                self.scheduled_tasks_by_project[project_id] = []
            if task.scheduled_start and task.scheduled_end:
                self.scheduled_tasks_by_project[project_id].append(task)

    def score_slot(self, slot: TimeSlot, task: Task) -> SlotScore:
        factors = {
            "work_hour_alignment": self.score_work_hour_alignment(slot),
            "energy_level_match": self.score_energy_level_match(slot, task),
            "project_proximity": self.score_project_proximity(slot, task),
            "buffer_adequacy": self.score_buffer_adequacy(slot),
            "time_preference": self.score_time_preference(slot, task),
            "deadline_proximity": self.score_deadline_proximity(slot, task),
            "priority_score": self.score_priority(task),
        }

        weights = {
            "work_hour_alignment": 1.0,
            "energy_level_match": 1.5,
            "project_proximity": 0.5,
            "buffer_adequacy": 0.8,
            "time_preference": 1.2,
            "deadline_proximity": 3.0,
            "priority_score": 1.8,
        }

        total_weight = sum(weights.values())
        weighted_sum = sum(factors[key] * weights[key] for key in factors)
        total_score = weighted_sum / total_weight if total_weight > 0 else 0

        return SlotScore(total=total_score, factors=factors)

    def score_work_hour_alignment(self, slot: TimeSlot) -> float:
        # Giả định settings có 'work_start_hour' và 'work_end_hour'
        work_start = self.settings.get('work_start_hour', 9)
        work_end = self.settings.get('work_end_hour', 17)
        return 1.0 if work_start <= slot.start.hour < work_end else 0.0

    def score_energy_level_match(self, slot: TimeSlot, task: Task) -> float:
        if not task.energy_level: return 0.5 # Điểm trung lập nếu không có mức năng lượng

        # Giả định energy_level có thể là "high", "medium", "low"
        energy_levels_order = ["low", "medium", "high"]
        task_energy = task.energy_level.lower()

        # Lấy mức năng lượng của slot dựa trên giờ trong ngày (cần hàm helper)
        slot_energy = self.get_energy_level_for_time(slot.start.hour) # Cần hàm get_energy_level_for_time

        if not slot_energy: return 0.5 # Điểm trung lập nếu không xác định được năng lượng

        try:
            task_energy_index = energy_levels_order.index(task_energy)
            slot_energy_index = energy_levels_order.index(slot_energy)
            distance = abs(task_energy_index - slot_energy_index)
            if distance == 0: return 1.0 # Khớp hoàn toàn
            elif distance == 1: return 0.5 # Gần khớp
            else: return 0.0 # Không khớp
        except ValueError:
            return 0.5 # Lỗi khi tìm index

    def get_energy_level_for_time(self, hour: int) -> Optional[str]:
        # Hàm ví dụ để xác định mức năng lượng theo giờ
        # Cần tùy chỉnh dựa trên cấu hình của bạn
        if 6 <= hour < 10: return "high"       # Buổi sáng sớm: năng lượng cao
        elif 10 <= hour < 12: return "medium"  # Trước trưa: năng lượng vừa
        elif 12 <= hour < 14: return "low"     # Buổi trưa: năng lượng thấp (nghỉ ngơi)
        elif 14 <= hour < 17: return "high"    # Buổi chiều: năng lượng cao trở lại
        elif 17 <= hour < 20: return "medium"  # Buổi tối: năng lượng vừa
        else: return "low" # Đêm muộn/sáng sớm: năng lượng thấp

    def score_buffer_adequacy(self, slot: TimeSlot) -> float:
        # Hiện tại chỉ là điểm boolean đơn giản
        # Trong thực tế có thể dựa vào duration của slot so với task
        return 1.0 if slot.duration_minutes >= self.settings.get('min_buffer_minutes', 15) else 0.0

    def score_time_preference(self, slot: TimeSlot, task: Task) -> float:
        if task.preferred_time:
            hour = slot.start.hour
            preference = task.preferred_time.lower()
            ranges = {
                "morning": (5, 12),
                "afternoon": (12, 17),
                "evening": (17, 22),
            }
            if preference in ranges:
                start_hour, end_hour = ranges[preference]
                return 1.0 if start_hour <= hour < end_hour else 0.0
            return 0.0 # Không nhận diện được preference

        # Nếu không có preference cụ thể, ưu tiên các slot sớm hơn trong ngày
        now = datetime.datetime.now()
        minutes_to_slot = (slot.start - now).total_seconds() / 60
        days_to_slot = minutes_to_slot / (24 * 60)
        # Giảm dần về 0.5 sau 7 ngày
        return max(0, min(1.0, 0.5 + 0.5 * (1 - days_to_slot / 7))) if days_to_slot < 7 else 0.5

    def score_deadline_proximity(self, slot: TimeSlot, task: Task) -> float:
        if not task.due_date:
            return 0.5 # Điểm trung lập nếu không có hạn chót

        now = datetime.datetime.now()
        minutes_to_deadline = (task.due_date - now).total_seconds() / 60
        minutes_to_slot = (slot.start - now).total_seconds() / 60

        if minutes_to_deadline < 0: # Đã quá hạn
            days_overdue = abs(minutes_to_deadline) / (24 * 60)
            # Điểm ban đầu cao hơn, giảm dần theo thời gian slot
            base_score = min(2.0, 1.0 + days_overdue / 7) # Tăng gấp đôi sau 1 tuần
            time_penalty = min(0.5, minutes_to_slot / (14 * 24 * 60)) # Giảm tối đa 50% nếu slot cách 2 tuần
            return base_score * (1 - time_penalty)
        else: # Chưa quá hạn
            days_to_deadline = minutes_to_deadline / (24 * 60)
            # Điểm cao khi gần deadline, giảm dần
            score = min(0.99, (days_to_deadline / 3) if days_to_deadline < 3 else 0.1) # Giảm nhanh trong 3 ngày đầu
            return max(0.1, score) # Đảm bảo điểm không quá thấp

    def score_project_proximity(self, slot: TimeSlot, task: Task) -> float:
        project_id = getattr(task, 'project_id', None)
        if not project_id or not self.settings.get('group_by_project', False):
            return 0.5 # Điểm trung lập nếu không có ID dự án hoặc không group theo dự án

        project_tasks = self.scheduled_tasks_by_project.get(project_id, [])
        if not project_tasks:
            return 0.5 # Điểm trung lập nếu không có task nào khác trong dự án

        min_distance_hours = float('inf')
        for p_task in project_tasks:
            if p_task.scheduled_start and p_task.scheduled_end:
                # Tính khoảng cách tới start và end của task đã lên lịch
                dist_to_start = abs((slot.start - p_task.scheduled_start).total_seconds() / 3600)
                dist_to_end = abs((slot.end - p_task.scheduled_end).total_seconds() / 3600)
                min_distance_hours = min(min_distance_hours, dist_to_start, dist_to_end)

        # Điểm giảm dần theo khoảng cách (ví dụ: khớp hoàn toàn là 1, 4 tiếng là 0.5)
        return max(0, min(1.0, 1.0 - min_distance_hours / 4))

    def score_priority(self, task: Task) -> float:
        if not task.priority or task.priority == Priority.LOW:
            return 0.25 # Điểm thấp cho ưu tiên thấp/không có

        priority_map = {
            Priority.HIGH: 1.0,
            Priority.MEDIUM: 0.75,
            Priority.CRITICAL: 1.2, # Ưu tiên cao nhất
        }
        return priority_map.get(task.priority, 0.25) # Mặc định là 0.25 nếu không tìm thấy


