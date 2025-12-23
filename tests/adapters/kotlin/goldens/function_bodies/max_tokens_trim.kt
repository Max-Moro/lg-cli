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
        repo = repository
        createdAt = Instant.now()
        // … init body truncated
    }

    // secondary constructor
    constructor(repository: TaskRepository, initialTasks: List<Task>) : this(repository) {
        for (task in initialTasks) {
            pendingTasks.add(task.id)
        // … constructor body truncated (2 lines)
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
        require(title.isNotBlank()) { "Title cannot be blank" }

        // … method body truncated (8 lines)
        return saved
    }

    // internal KDoc in method body
    suspend fun assignTask(taskId: String, assignee: String): Task? {
        /**
         * Assignment logic explanation:
         * First validates the task exists, then checks assignee availability,
         * and finally performs the atomic assignment operation.
         */

        // … method body truncated (2 lines)
        return repo.save(updated)
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
            println("Checking notification status")
            return _enabled
        }
        set(value) {
            println("Setting notifications: $value")
            _enabled = value
        }

    // computed property with getter
    val statusMessage: String
        get() {
            // … getter body truncated
            return "Notifications are $status"
        }

    fun notifyAssignment(task: Task, assignee: String) {
        if (!enabled) return

        // … method body truncated (2 lines)
    }

    // nested function inside method
    private fun buildNotificationMessage(task: Task, assignee: String): String {
        // … method body truncated (9 lines)
        return "$priorityText: ${task.title} assigned to $assignee"
    }

    private fun sendNotification(recipient: String, message: String) {
        println("Sending to $recipient: $message")
    }
}

// object declaration
object TaskIdGenerator {
    private var counter: Long = 0

    fun nextId(prefix: String = "TASK"): String {
        counter++
        // … method body truncated
        return "$prefix-$timestamp-$counter"
    }

    fun reset() {
        counter = 0
        println("ID generator reset")
    }
}

class TaskFormatter {
    // companion object
    companion object {
        fun formatShort(task: Task): String {
            // … method body truncated
            return "[$priority] ${task.title}"
        }

        fun formatDetailed(task: Task): String {
            // … method body truncated (5 lines)
            return lines.joinToString("\n")
        }
    }
}

// extension function on generic type
fun List<Task>.filterByPriority(minPriority: Priority): List<Task> {
    return filter { it.priority.ordinal >= minPriority.ordinal }
        .sortedByDescending { it.priority.ordinal }
}

// extension function on String
fun String.toTaskTitle(): String {
    return trim()
        .split("\\s+".toRegex())
        .joinToString(" ") { word ->
            word.lowercase().replaceFirstChar { it.uppercase() }
        }
}

// generic suspend function
suspend fun <T> retryOperation(times: Int, block: suspend () -> T): T {
    var lastException: Exception? = null

    repeat(times) { attempt ->
    // … function body truncated (8 lines)
}

// multiline lambda with Comparator
val priorityComparator: Comparator<Task> = Comparator { a, b ->
    val priorityDiff = b.priority.ordinal - a.priority.ordinal
    // … lambda body truncated
}

// multiline lambda as function type
val taskValidator: (Task) -> Boolean = { task ->
    val titleValid = task.title.isNotBlank()
    // … lambda body truncated (2 lines)
}

// lambda with receiver
val taskTransformer: Task.() -> Task = {
    val normalizedTitle = title.trim().lowercase()
    copy(title = normalizedTitle)
}

// single-line lambda (should not be stripped)
val simpleValidator = { task: Task -> task.id.isNotEmpty() }

fun main() {
    println("Task Manager initialized")
    println(TaskIdGenerator.nextId())
}
