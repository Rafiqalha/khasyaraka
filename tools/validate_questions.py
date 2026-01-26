#!/usr/bin/env python3
"""
Question Dataset Validator

This tool validates the entire learning dataset to ensure data integrity.

Folder Structure Assumptions:
- app/data/section.json: All sections metadata
- app/data/units.json: All units metadata
- app/data/levels.json: All levels metadata
- app/data/question/<topic>/unit_*.json: Question bank files

How to Run:
    python tools/validate_questions.py

Validation Rules:
1. Schema Validation: Every question must validate against Question schema
2. Level Coverage: Each level must have at least MIN_QUESTIONS_PER_LEVEL questions
3. Orphan Detection: Detect questions/levels/units with invalid references
4. Duplicate Detection: Detect duplicate question IDs and order conflicts
5. Summary Report: Print comprehensive validation summary

Exit Codes:
- 0: All validations pass
- 1: Any validation error found
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.question_schema import Question, QuestionType, Difficulty


# ==================== CONFIGURATION ====================

MIN_QUESTIONS_PER_LEVEL = 6
DATA_DIR = Path(__file__).parent.parent / "app" / "data"
SECTIONS_FILE = DATA_DIR / "section.json"
UNITS_FILE = DATA_DIR / "units.json"
LEVELS_FILE = DATA_DIR / "levels.json"
QUESTIONS_DIR = DATA_DIR / "question"


# ==================== VALIDATION RESULTS ====================

@dataclass
class ValidationError:
    """Represents a single validation error"""
    file_path: str
    question_id: Optional[str]
    error_message: str
    error_type: str  # 'schema', 'orphan', 'duplicate', 'coverage'


@dataclass
class ValidationResults:
    """Aggregated validation results"""
    schema_errors: List[ValidationError] = field(default_factory=list)
    orphan_errors: List[ValidationError] = field(default_factory=list)
    duplicate_errors: List[ValidationError] = field(default_factory=list)
    coverage_errors: List[ValidationError] = field(default_factory=list)
    total_questions: int = 0
    total_levels: int = 0
    total_units: int = 0
    total_sections: int = 0
    levels_with_questions: Dict[str, int] = field(default_factory=dict)


# ==================== COLOR OUTPUT ====================

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_error(msg: str):
    """Print error message in red"""
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_success(msg: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_warning(msg: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_info(msg: str):
    """Print info message in cyan"""
    print(f"{Colors.CYAN}ℹ️  {msg}{Colors.RESET}")


def print_header(msg: str):
    """Print header message in bold"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


# ==================== DATA LOADING ====================

def load_json_file(file_path: Path) -> List[Dict]:
    """Load JSON file and return list of items"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except FileNotFoundError:
        print_error(f"File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def load_metadata() -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, Dict]]:
    """Load all metadata files"""
    print_info("Loading metadata files...")
    
    sections = {s['id']: s for s in load_json_file(SECTIONS_FILE)}
    units = {u['id']: u for u in load_json_file(UNITS_FILE)}
    levels = {l['id']: l for l in load_json_file(LEVELS_FILE)}
    
    print_success(f"Loaded {len(sections)} sections, {len(units)} units, {len(levels)} levels")
    
    return sections, units, levels


def load_question_files() -> List[Tuple[Path, Dict]]:
    """Load all question bank files"""
    print_info("Loading question bank files...")
    
    question_files = []
    if not QUESTIONS_DIR.exists():
        print_error(f"Questions directory not found: {QUESTIONS_DIR}")
        sys.exit(1)
    
    for question_file in QUESTIONS_DIR.rglob("unit_*.json"):
        try:
            with open(question_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                question_files.append((question_file, data))
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in {question_file}: {e}")
            sys.exit(1)
    
    print_success(f"Found {len(question_files)} question bank files")
    return question_files


# ==================== VALIDATION FUNCTIONS ====================

def validate_schema(question_file: Path, question_data: Dict, results: ValidationResults):
    """
    Validate question against schema with backward compatibility support.
    
    Handles legacy data formats:
    - Missing schema_version: defaults to "1.0"
    - Legacy type names: fill_blank -> input, word_bank -> ordering
    - Answers in payload: migrates to answer field (for validation only)
    """
    questions = question_data.get('questions', [])
    
    for idx, q_data in enumerate(questions):
        question_id = q_data.get('id', f'unknown_{idx}')
        try:
            # Set default schema_version for backward compatibility
            if 'schema_version' not in q_data:
                q_data['schema_version'] = '1.0'
            
            # Convert legacy type names to canonical types
            legacy_type = q_data.get('type', '')
            if legacy_type == 'fill_blank':
                q_data['type'] = 'input'
            elif legacy_type == 'word_bank':
                q_data['type'] = 'ordering'
            
            # Set default difficulty if missing
            if 'difficulty' not in q_data:
                q_data['difficulty'] = 'medium'
            
            # Set default order if missing (use index + 1)
            if 'order' not in q_data:
                q_data['order'] = idx + 1
            
            # Ensure tags field exists
            if 'tags' not in q_data:
                q_data['tags'] = []
            
            # Ensure extensions field exists
            if 'extensions' not in q_data:
                q_data['extensions'] = {}
            
            # Migrate answers from payload to answer field (for legacy data)
            # This is a migration helper - new data should have answers in answer field
            payload = q_data.get('payload', {})
            answer = q_data.get('answer')
            
            if not answer and isinstance(payload, dict):
                # Try to extract answer from payload (legacy format)
                q_type = q_data.get('type', '')
                
                if q_type == 'multiple_choice' and 'correct_answer' in payload:
                    # Extract correct index
                    options = payload.get('options', [])
                    correct_answer = payload.get('correct_answer')
                    if correct_answer in options:
                        correct_index = options.index(correct_answer)
                        q_data['answer'] = {'correct_index': correct_index}
                        # Remove answer from payload
                        payload = payload.copy()
                        payload.pop('correct_answer', None)
                        q_data['payload'] = payload
                
                elif q_type == 'input' and 'correct_answer' in payload:
                    # Extract answer
                    q_data['answer'] = {
                        'correct_answer': payload.get('correct_answer'),
                        'alternatives': payload.get('accept_alternatives')
                    }
                    # Remove answer from payload
                    payload = payload.copy()
                    payload.pop('correct_answer', None)
                    payload.pop('accept_alternatives', None)
                    q_data['payload'] = payload
                
                elif q_type == 'ordering' and 'correct_order' in payload:
                    # Extract answer
                    q_data['answer'] = {'correct_order': payload.get('correct_order')}
                    # Remove answer from payload
                    payload = payload.copy()
                    payload.pop('correct_order', None)
                    q_data['payload'] = payload
                
                elif q_type == 'true_false' and 'correct_answer' in payload:
                    # Extract answer
                    q_data['answer'] = {'correct_answer': payload.get('correct_answer')}
                    # Remove answer from payload
                    payload = payload.copy()
                    payload.pop('correct_answer', None)
                    q_data['payload'] = payload
            
            # Ensure payload has type discriminator for discriminated union
            if isinstance(q_data.get('payload'), dict) and 'type' not in q_data['payload']:
                q_data['payload']['type'] = q_data.get('type')
            
            # Validate against schema
            Question(**q_data)
            results.total_questions += 1
            
        except Exception as e:
            error = ValidationError(
                file_path=str(question_file),
                question_id=question_id,
                error_message=str(e),
                error_type='schema'
            )
            results.schema_errors.append(error)


def validate_orphans(
    questions: List[Dict],
    levels: Dict[str, Dict],
    units: Dict[str, Dict],
    sections: Dict[str, Dict],
    results: ValidationResults
):
    """Detect orphan entities"""
    # Check questions with invalid level_id
    for q in questions:
        level_id = q.get('level_id')
        if level_id and level_id not in levels:
            error = ValidationError(
                file_path="",
                question_id=q.get('id'),
                error_message=f"Question references non-existent level: {level_id}",
                error_type='orphan'
            )
            results.orphan_errors.append(error)
    
    # Check levels with invalid unit_id
    for level_id, level in levels.items():
        unit_id = level.get('unit_id')
        if unit_id and unit_id not in units:
            error = ValidationError(
                file_path="levels.json",
                question_id=None,
                error_message=f"Level {level_id} references non-existent unit: {unit_id}",
                error_type='orphan'
            )
            results.orphan_errors.append(error)
    
    # Check units with invalid section_id
    for unit_id, unit in units.items():
        section_id = unit.get('section_id')
        if section_id and section_id not in sections:
            error = ValidationError(
                file_path="units.json",
                question_id=None,
                error_message=f"Unit {unit_id} references non-existent section: {section_id}",
                error_type='orphan'
            )
            results.orphan_errors.append(error)
    
    # Check units with zero levels
    level_counts = defaultdict(int)
    for level in levels.values():
        unit_id = level.get('unit_id')
        if unit_id:
            level_counts[unit_id] += 1
    
    for unit_id, unit in units.items():
        if level_counts[unit_id] == 0:
            error = ValidationError(
                file_path="units.json",
                question_id=None,
                error_message=f"Unit {unit_id} has no levels",
                error_type='orphan'
            )
            results.orphan_errors.append(error)


def validate_duplicates(questions: List[Dict], results: ValidationResults):
    """Detect duplicate question IDs and order conflicts"""
    seen_ids: Set[str] = set()
    level_orders: Dict[str, Set[int]] = defaultdict(set)
    
    for q in questions:
        question_id = q.get('id')
        level_id = q.get('level_id')
        order = q.get('order')
        
        # Check duplicate IDs
        if question_id:
            if question_id in seen_ids:
                error = ValidationError(
                    file_path="",
                    question_id=question_id,
                    error_message=f"Duplicate question ID: {question_id}",
                    error_type='duplicate'
                )
                results.duplicate_errors.append(error)
            seen_ids.add(question_id)
        
        # Check duplicate orders within same level
        if level_id and order:
            if order in level_orders[level_id]:
                error = ValidationError(
                    file_path="",
                    question_id=question_id,
                    error_message=f"Duplicate order {order} in level {level_id}",
                    error_type='duplicate'
                )
                results.duplicate_errors.append(error)
            level_orders[level_id].add(order)


def validate_coverage(questions: List[Dict], levels: Dict[str, Dict], results: ValidationResults):
    """Validate minimum question coverage per level"""
    level_question_counts = defaultdict(int)
    
    for q in questions:
        level_id = q.get('level_id')
        if level_id:
            level_question_counts[level_id] += 1
    
    for level_id, level in levels.items():
        count = level_question_counts[level_id]
        results.levels_with_questions[level_id] = count
        
        if count < MIN_QUESTIONS_PER_LEVEL:
            error = ValidationError(
                file_path="levels.json",
                question_id=None,
                error_message=f"Level {level_id} has only {count} questions (minimum: {MIN_QUESTIONS_PER_LEVEL})",
                error_type='coverage'
            )
            results.coverage_errors.append(error)


# ==================== MAIN VALIDATION ====================

def run_validation() -> ValidationResults:
    """Run all validations"""
    results = ValidationResults()
    
    # Load metadata
    sections, units, levels = load_metadata()
    results.total_sections = len(sections)
    results.total_units = len(units)
    results.total_levels = len(levels)
    
    # Load question files
    question_files = load_question_files()
    all_questions = []
    
    # Validate each question file
    print_header("Validating Question Files")
    for question_file, question_data in question_files:
        print_info(f"Validating: {question_file.name}")
        questions = question_data.get('questions', [])
        all_questions.extend(questions)
        
        # Schema validation
        validate_schema(question_file, question_data, results)
    
    # Cross-file validations
    print_header("Running Cross-File Validations")
    
    print_info("Validating orphan entities...")
    validate_orphans(all_questions, levels, units, sections, results)
    
    print_info("Validating duplicates...")
    validate_duplicates(all_questions, results)
    
    print_info("Validating level coverage...")
    validate_coverage(all_questions, levels, results)
    
    return results


# ==================== REPORTING ====================

def print_errors(errors: List[ValidationError], error_type: str):
    """Print grouped errors"""
    if not errors:
        return
    
    print(f"\n{Colors.BOLD}{Colors.RED}{error_type.upper()} ERRORS ({len(errors)}):{Colors.RESET}")
    
    # Group by file
    by_file = defaultdict(list)
    for error in errors:
        by_file[error.file_path or 'unknown'].append(error)
    
    for file_path, file_errors in by_file.items():
        print(f"\n  {Colors.YELLOW}File: {file_path}{Colors.RESET}")
        for error in file_errors:
            question_ref = f" (Question: {error.question_id})" if error.question_id else ""
            print(f"    • {error.error_message}{question_ref}")


def print_summary(results: ValidationResults):
    """Print validation summary"""
    print_header("Validation Summary")
    
    print(f"{Colors.BOLD}Dataset Statistics:{Colors.RESET}")
    print(f"  Sections: {results.total_sections}")
    print(f"  Units: {results.total_units}")
    print(f"  Levels: {results.total_levels}")
    print(f"  Questions: {results.total_questions}")
    
    print(f"\n{Colors.BOLD}Validation Results:{Colors.RESET}")
    print(f"  Schema Errors: {len(results.schema_errors)}")
    print(f"  Orphan Errors: {len(results.orphan_errors)}")
    print(f"  Duplicate Errors: {len(results.duplicate_errors)}")
    print(f"  Coverage Errors: {len(results.coverage_errors)}")
    
    total_errors = (
        len(results.schema_errors) +
        len(results.orphan_errors) +
        len(results.duplicate_errors) +
        len(results.coverage_errors)
    )
    
    if total_errors == 0:
        print_success("\n🎉 All validations passed!")
        return True
    else:
        print_error(f"\n❌ Found {total_errors} validation error(s)")
        
        # Print detailed errors
        print_errors(results.schema_errors, "Schema")
        print_errors(results.orphan_errors, "Orphan")
        print_errors(results.duplicate_errors, "Duplicate")
        print_errors(results.coverage_errors, "Coverage")
        
        return False


# ==================== MAIN ====================

def main():
    """Main entry point"""
    print_header("Question Dataset Validator")
    print_info("Starting validation...")
    
    try:
        results = run_validation()
        success = print_summary(results)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_error("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
