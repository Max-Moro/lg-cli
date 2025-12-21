/**
 * Task management library for team collaboration.
 */

package com.example.taskmanager

import kotlinx.coroutines.delay
import java.time.Instant
import java.util.UUID

data class Task(
    val id: String,
    val title: String,
    val description: String,
    val priority: Priority,
    val assignee: String? = null
)

enum class Priority { LOW, MEDIUM, HIGH, CRITICAL }

interface TaskRepository {
    suspend fun findById(id: String): Task?
    suspend fun save(task: Task): Task
    suspend fun delete(id: String): Boolean
}

// external KDoc on class
/**
 * Core task management service.
 *
 * Handles creation, updates, and lifecycle of tasks.
 * Thread-safe for concurrent access.
 */
class TaskService(repository: TaskRepository) {
    private val repo: TaskRepository
    private val createdAt: Instant

    // init block
    init {
        // … init body omitted (3 lines)
    }

    // secondary constructor
    constructor(repository: TaskRepository, initialTasks: List<Task>) : this(repository) {
        // … constructor body omitted (4 lines)
    }

    private val pendingTasks = mutableSetOf<String>()

    // external KDoc on method, suspend function
    /**
     * Creates a new task with validation.
     *
     * @param title Task title, must not be blank
     * @param description Detailed description
     * @param priority Task priority level
     * @return Created task with generated ID
     */
    suspend fun createTask(title: String, description: String, priority: Priority): Task {
        // … method body omitted (10 lines)
    }

    // internal KDoc in method body
    suspend fun assignTask(taskId: String, assignee: String): Task? {
        /**
         * Assignment logic explanation:
         * First validates the task exists, then checks assignee availability,
         * and finally performs the atomic assignment operation.
         */
        // … method body omitted (3 lines)
    }

    // single-line body (should not be stripped)
    fun getPendingCount(): Int {
        return pendingTasks.size
    }
}

class TaskNotificationService {
    private var _enabled: Boolean = true

    // custom getter & setter
    var enabled: Boolean
        get() {
            // … getter body omitted (2 lines)
        }
        set(value) {
            // … setter body omitted (2 lines)
        }

    // computed property with getter
    val statusMessage: String
        get() {
            // … getter body omitted (2 lines)
        }

    fun notifyAssignment(task: Task, assignee: String) {
        // … method body omitted (3 lines)
    }

    // nested function inside method
    private fun buildNotificationMessage(task: Task, assignee: String): String {
        // … method body omitted (10 lines)
    }

    private fun sendNotification(recipient: String, message: String) {
        println("Sending to $recipient: $message")
    }
}

// object declaration
object TaskIdGenerator {
    private var counter: Long = 0

    fun nextId(prefix: String = "TASK"): String {
        // … method body omitted (3 lines)
    }

    fun reset() {
        // … method body omitted (2 lines)
    }
}

class TaskFormatter {
    // companion object
    companion object {
        fun formatShort(task: Task): String {
            // … method body omitted (2 lines)
        }

        fun formatDetailed(task: Task): String {
            // … method body omitted (6 lines)
        }
    }
}

// extension function on generic type
fun List<Task>.filterByPriority(minPriority: Priority): List<Task> {
    // … function body omitted (2 lines)
}

// extension function on String
fun String.toTaskTitle(): String {
    // … function body omitted (5 lines)
}

// generic suspend function
suspend fun <T> retryOperation(times: Int, block: suspend () -> T): T {
    // … function body omitted (10 lines)
}

// multiline lambda with Comparator
val priorityComparator: Comparator<Task> = Comparator { a, b ->
    // … lambda body omitted (2 lines)
}

// multiline lambda as function type
val taskValidator: (Task) -> Boolean = { task ->
    // … lambda body omitted (3 lines)
}

// lambda with receiver
val taskTransformer: Task.() -> Task = {
    // … lambda body omitted (2 lines)
}

// single-line lambda (should not be stripped)
val simpleValidator = { task: Task -> task.id.isNotEmpty() }

fun main() {
    // … function body omitted (2 lines)
}
