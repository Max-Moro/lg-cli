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
        println("TaskService initialized at $createdAt")
    }

    // secondary constructor
    constructor(repository: TaskRepository, initialTasks: List<Task>) : this(repository) {
        for (task in initialTasks) {
            pendingTasks.add(task.id)
        }
        println("Loaded ${initialTasks.size} initial tasks")
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

        val task = Task(
            id = UUID.randomUUID().toString(),
            title = title.trim(),
            description = description,
            priority = priority
        )

        val saved = repo.save(task)
        pendingTasks.add(saved.id)
        return saved
    }

    // internal KDoc in method body
    suspend fun assignTask(taskId: String, assignee: String): Task? {
        /**
         * Assignment logic explanation:
         * First validates the task exists, then checks assignee availability,
         * and finally performs the atomic assignment operation.
         */
        val task = repo.findById(taskId) ?: return null

        val updated = task.copy(assignee = assignee)
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
            val status = if (enabled) "active" else "disabled"
            return "Notifications are $status"
        }

    fun notifyAssignment(task: Task, assignee: String) {
        if (!enabled) return

        val message = buildNotificationMessage(task, assignee)
        sendNotification(assignee, message)
    }

    // nested function inside method
    private fun buildNotificationMessage(task: Task, assignee: String): String {
        fun formatPriority(p: Priority): String {
            return when (p) {
                Priority.CRITICAL -> "[!] CRITICAL"
                Priority.HIGH -> "[H] High"
                Priority.MEDIUM -> "[M] Medium"
                Priority.LOW -> "[L] Low"
            }
        }

        val priorityText = formatPriority(task.priority)
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
        val timestamp = System.currentTimeMillis()
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
            val priority = task.priority.name.first()
            return "[$priority] ${task.title}"
        }

        fun formatDetailed(task: Task): String {
            val lines = mutableListOf<String>()
            lines.add("Task: ${task.title}")
            lines.add("Priority: ${task.priority}")
            lines.add("Description: ${task.description}")
            task.assignee?.let { lines.add("Assignee: $it") }
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
        try {
            return block()
        } catch (e: Exception) {
            lastException = e
            delay(100L * (attempt + 1))
        }
    }

    throw lastException ?: IllegalStateException("Retry failed")
}

// multiline lambda with Comparator
val priorityComparator: Comparator<Task> = Comparator { a, b ->
    val priorityDiff = b.priority.ordinal - a.priority.ordinal
    if (priorityDiff != 0) priorityDiff else a.title.compareTo(b.title)
}

// multiline lambda as function type
val taskValidator: (Task) -> Boolean = { task ->
    val titleValid = task.title.isNotBlank()
    val idValid = task.id.isNotEmpty()
    titleValid && idValid
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
