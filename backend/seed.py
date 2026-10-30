import uuid

from backend.models import Card, Deck
from backend.storage import save_seed_deck


_SEED_NAMESPACE = uuid.UUID("62366ac1-fb8c-498d-9e13-3b55fd8c70a6")


def _q(question, answer, wrong_answers, explanation, difficulty="medium"):
    return {
        "question": question,
        "answer": answer,
        "options": [answer, *wrong_answers],
        "explanation": explanation,
        "difficulty": difficulty,
    }


SEED_DECKS = [
    {
        "slug": "python",
        "title": "Python Fundamentals",
        "category": "Python",
        "cards": [
            _q("Which statement best describes a Python list?", "It is an ordered, mutable sequence.", ["It is an unordered immutable set.", "It stores only numeric values.", "It is a key-value mapping."], "Lists preserve order and can be changed after creation.", "easy"),
            _q("What does a tuple provide compared with a list?", "An ordered sequence that cannot be reassigned item by item.", ["A mapping from unique keys to values.", "An automatically sorted mutable sequence.", "A collection that permits only integers."], "Tuples are ordered sequences, and their item references cannot be reassigned.", "easy"),
            _q("What must be true of dictionary keys?", "They must be hashable.", ["They must all be strings.", "They must be unique across every dictionary.", "They must be mutable."], "Python dictionaries require hashable keys so they can be looked up efficiently.", "medium"),
            _q("What is the result of `len({'a': 1, 'b': 2})`?", "2", ["1", "3", "An error because dictionaries have no length."], "The length of a dictionary is the number of key-value pairs.", "easy"),
            _q("What does `enumerate(items)` commonly provide in a loop?", "An index and the corresponding item.", ["Only the items in reverse order.", "A sorted copy of the items.", "A count of matching values."], "Each iteration of enumerate yields an index-item pair.", "easy"),
            _q("In `values[1:4]`, which indexes are included?", "Indexes 1, 2, and 3.", ["Indexes 1, 2, 3, and 4.", "Indexes 0 through 4.", "Only indexes 1 and 4."], "A Python slice includes its start and excludes its stop.", "easy"),
            _q("What does a set primarily guarantee about its elements?", "Elements are unique.", ["Elements remain in insertion order in every operation.", "Elements can be accessed by numeric index.", "Elements are automatically sorted."], "Sets discard duplicate elements and support membership operations.", "easy"),
            _q("What does `is` compare in Python?", "Object identity.", ["Whether two values have the same type only.", "Whether two objects have equal contents.", "Whether two variables have the same name."], "The `is` operator tests whether references point to the same object.", "medium"),
            _q("What is a generator useful for?", "Producing values lazily as they are requested.", ["Storing every possible value in memory up front.", "Making a function run in parallel automatically.", "Converting any function into a class."], "Generators yield values on demand and can reduce memory use for large sequences.", "medium"),
            _q("What does a `with` statement commonly manage?", "Setup and cleanup of a context-managed resource.", ["Automatic conversion of all exceptions into return values.", "Parallel execution of the block.", "A loop that repeats until a condition is true."], "Context managers reliably perform cleanup when a block exits.", "medium"),
            _q("Which clause handles a matching exception in Python?", "`except`", ["`ensure`", "`catch`", "`recover`"], "An except clause handles exceptions raised in its associated try block.", "easy"),
            _q("When is code under `if __name__ == '__main__':` run?", "When the module is executed as the main program.", ["Whenever the module is imported.", "Only when Python is in interactive mode.", "Only after every function in the module is called."], "Python sets __name__ to __main__ when a file is run directly.", "medium"),
            _q("Why are mutable default argument values usually avoided?", "The same object is reused across calls.", ["Python rejects every mutable default.", "They make all calls execute asynchronously.", "They are copied only after the function returns."], "A default object is created once when the function is defined, not per call.", "hard"),
            _q("What does a virtual environment isolate?", "A project's installed Python packages.", ["The project's source code from the operating system.", "A process from CPU scheduling.", "Python syntax from the interpreter."], "Virtual environments provide separate dependency installations for projects.", "easy"),
            _q("What does a list comprehension create?", "A new list from an iterable, optionally filtering or transforming items.", ["A generator that always evaluates lazily.", "A dictionary with automatically unique keys.", "A loop that modifies the source iterable in place."], "List comprehensions build a list from an iterable expression.", "medium"),
        ],
    },
    {
        "slug": "pandas-numpy",
        "title": "pandas and NumPy Essentials",
        "category": "Data Science",
        "cards": [
            _q("What does a pandas DataFrame represent?", "A two-dimensional labeled tabular data structure.", ["A one-dimensional unlabeled array only.", "A database server process.", "A chart with fixed numeric axes."], "A DataFrame organizes data in labeled rows and columns.", "easy"),
            _q("What is a pandas Series?", "A one-dimensional labeled array.", ["A two-dimensional table with multiple indexes.", "A NumPy function for sorting arrays.", "A SQL query result requiring a database connection."], "A Series pairs values with an index.", "easy"),
            _q("What does `df.iloc[0]` select?", "The row at integer position zero.", ["The row whose index label is the string '0' only.", "The first column by name.", "All rows with missing values."], "`iloc` uses integer positions for selection.", "easy"),
            _q("What does `df.loc['row_a']` select?", "Data associated with the index label 'row_a'.", ["The row at integer position 'row_a'.", "A column named 'row_a' in every case.", "The first row regardless of its label."], "`loc` selects using index and column labels.", "easy"),
            _q("How can missing values be identified in a pandas object?", "With `isna()` or its alias `isnull()`.", ["With `isblank()`.", "Only by comparing values to an empty string.", "With `missing()`."], "The pandas `isna` method marks missing values such as NaN and None.", "easy"),
            _q("What does `groupby` followed by `mean` do?", "Computes group-wise means for eligible columns.", ["Sorts all rows alphabetically.", "Fills missing values with the global mean.", "Combines two tables using matching keys."], "Grouping partitions rows by keys before applying an aggregation.", "medium"),
            _q("What is the default join behavior of `pandas.merge`?", "An inner join on shared column names when no other keys are given.", ["A full outer join on every column.", "A left join using row positions.", "A cross join with no matching condition."], "The default merge is inner and uses the intersection of column names as keys.", "hard"),
            _q("What does NumPy broadcasting allow?", "Compatible array shapes to participate in element-wise operations.", ["Arrays of any shapes to be concatenated without checks.", "A scalar to change an array's dtype in place.", "A Python loop to run on multiple machines."], "Broadcasting virtually expands compatible dimensions for vectorized operations.", "medium"),
            _q("What is a common property of a NumPy ndarray?", "Its elements generally share a single dtype.", ["It stores only strings.", "It can contain only one dimension.", "It automatically sorts values after each assignment."], "NumPy arrays are homogeneous, supporting efficient numeric operations.", "easy"),
            _q("What does a boolean mask commonly do with a DataFrame?", "Selects rows or values where the corresponding condition is true.", ["Renames every column to a boolean value.", "Converts all numeric columns to booleans permanently.", "Sorts rows by the condition's source column."], "Boolean indexing filters data using a same-shape or aligned condition.", "medium"),
            _q("What does `axis=0` mean for a pandas reduction such as `sum`?", "Reduce down rows to produce a result for each column.", ["Reduce across columns to produce one result per row.", "Always remove the index and columns.", "Apply the reduction only to the first row."], "For DataFrame reductions, axis 0 is the row axis; values are reduced vertically per column.", "hard"),
            _q("What does `pd.read_csv(path)` usually return?", "A DataFrame loaded from delimited text.", ["A NumPy scalar.", "A database connection.", "A matplotlib figure."], "The CSV reader parses tabular text into a DataFrame by default.", "easy"),
            _q("Which operation adds a new column derived from existing columns?", "Assign a Series or expression to `df['new_column']`.", ["Call `df.index()`.", "Use `df.read_csv()`.", "Call `df.groupby()` without an aggregation."], "Assigning by column label creates or replaces a DataFrame column.", "medium"),
            _q("What is vectorization in NumPy?", "Applying operations to arrays without writing an explicit Python loop over each element.", ["Converting a one-dimensional array into a graph.", "Running each array element in a separate process.", "Replacing every number with a vector object."], "Vectorized operations use optimized array routines and concise element-wise expressions.", "medium"),
            _q("What does `dropna()` do by default on a DataFrame?", "Drops rows containing at least one missing value.", ["Replaces missing values with zero.", "Drops columns containing any text.", "Sorts rows with missing values last."], "By default, dropna removes rows with missing values in any column.", "medium"),
        ],
    },
    {
        "slug": "linux",
        "title": "Linux Command Line Essentials",
        "category": "Linux",
        "cards": [
            _q("Which command prints the current working directory?", "`pwd`", ["`cd`", "`mkdir`", "`touch`"], "`pwd` displays the current directory path.", "easy"),
            _q("What does `ls -la` show?", "Directory entries including hidden files and detailed metadata.", ["Only running processes.", "Disk partitions and mount points.", "Network routes and interfaces."], "`-a` includes hidden entries and `-l` uses a detailed listing format.", "easy"),
            _q("What does `chmod` change?", "File or directory permissions.", ["File contents.", "The machine hostname.", "The Linux kernel version."], "`chmod` changes read, write, and execute permissions.", "easy"),
            _q("Which command searches text for matching patterns?", "`grep`", ["`mv`", "`chmod`", "`pwd`"], "`grep` selects lines matching a pattern.", "easy"),
            _q("What is systemd commonly responsible for on Linux systems?", "Managing system services and units.", ["Editing source code.", "Compiling every application.", "Providing a command-line text editor."], "systemd is an init system and service manager used by many distributions.", "medium"),
            _q("What does `sudo` commonly allow?", "Running a command with permitted elevated or other-user privileges.", ["Compressing files without a compressor.", "Changing screen resolution only.", "Starting a browser as a background service."], "`sudo` runs a command according to configured privilege policy.", "medium"),
            _q("Where are many system-wide configuration files stored?", "`/etc`", ["`/proc`", "`/dev`", "`/var/tmp`"], "The `/etc` directory commonly contains host-specific configuration.", "easy"),
            _q("Which command provides a snapshot of running processes?", "`ps`", ["`mkdir`", "`grep`", "`touch`"], "`ps` reports process information at the time it is run.", "easy"),
            _q("What does `mkdir -p a/b` do?", "Creates the directory path, including missing parent directories.", ["Deletes `a` if it already exists.", "Creates a regular file named `a/b`.", "Changes ownership of both directories."], "The `-p` option creates parent directories as needed and does not fail if they exist.", "medium"),
            _q("What does a symbolic link contain?", "A path referring to another filesystem entry.", ["A complete duplicate copy of the target's data.", "A compressed archive of the target.", "A list of the target's file permissions only."], "A symbolic link stores a pathname that the filesystem resolves.", "medium"),
            _q("What does `cat file.txt` normally do?", "Writes the file's contents to standard output.", ["Edits the file interactively.", "Prints only its permissions.", "Moves it to the current directory."], "`cat` concatenates files to standard output and is often used to display short files.", "easy"),
            _q("Which command changes the current directory?", "`cd`", ["`pwd`", "`ls`", "`ps`"], "`cd` changes the shell's working directory.", "easy"),
            _q("What does `>` do in a typical shell command?", "Redirects standard output, replacing the destination file's contents.", ["Appends standard output to a file.", "Redirects standard error only.", "Runs the command with elevated privileges."], "Output redirection with `>` truncates or creates its destination file.", "medium"),
            _q("What is the purpose of `man command`?", "Displaying the command's manual page.", ["Installing the command automatically.", "Showing every process using the command.", "Changing the command's permissions."], "`man` opens locally available documentation pages.", "easy"),
            _q("What does `tar -x` generally indicate?", "Extracting files from an archive.", ["Creating a compressed archive.", "Listing user accounts.", "Changing file ownership."], "The `-x` option selects archive extraction in common tar implementations.", "medium"),
        ],
    },
    {
        "slug": "dbms-sql",
        "title": "DBMS and SQL",
        "category": "Databases",
        "cards": [
            _q("What property should a primary key have?", "It uniquely identifies each row and is not NULL.", ["It may repeat whenever rows share a category.", "It must contain a timestamp.", "It is always a foreign key to another table."], "A primary key enforces unique, non-NULL row identity.", "easy"),
            _q("What does a foreign key enforce?", "A reference to a key in another or the same table.", ["A unique value across every database table.", "Encryption of the referenced row.", "Automatic ordering of query results."], "Foreign keys help enforce referential integrity between related rows.", "easy"),
            _q("What does an SQL `SELECT` statement do?", "Retrieves rows and columns from a queryable source.", ["Deletes matching rows permanently.", "Defines a new database user.", "Changes a table's column type."], "`SELECT` queries data from tables and other supported sources.", "easy"),
            _q("Which clause filters rows before grouping?", "`WHERE`", ["`HAVING`", "`ORDER BY`", "`FROM`"], "`WHERE` filters source rows before grouping and aggregation.", "easy"),
            _q("Which clause filters groups after aggregation?", "`HAVING`", ["`WHERE`", "`JOIN`", "`VALUES`"], "`HAVING` applies a condition to groups, often using aggregate expressions.", "medium"),
            _q("What does an `INNER JOIN` return?", "Rows satisfying the join condition on both inputs.", ["Every left row whether matched or not.", "Every row from both inputs, matched or unmatched.", "Only rows with NULL join keys."], "An inner join includes combinations that satisfy its join condition.", "easy"),
            _q("What does a `LEFT JOIN` preserve?", "Every row from the left input, with NULLs for unmatched right-side columns.", ["Only rows that match on both sides.", "Every row from the right input only.", "Only unmatched rows from both inputs."], "A left join keeps all left-side rows and supplies NULLs where no right match exists.", "medium"),
            _q("What does `COUNT(*)` count?", "Rows in the selected group or result.", ["Only non-NULL values in the first column.", "Distinct values across all columns.", "The number of columns in a table."], "`COUNT(*)` counts rows, including rows with NULL values in some columns.", "medium"),
            _q("What does SQL `NULL` represent?", "A missing, unknown, or not-applicable value.", ["The numeric value zero.", "An empty string in every database.", "A Boolean false value."], "NULL is a marker for absent or unknown data and uses special comparison semantics.", "easy"),
            _q("What does `GROUP BY` do?", "Collects rows with matching grouping values for aggregation.", ["Sorts the result by every column.", "Removes duplicate rows from the table permanently.", "Combines two tables without a condition."], "`GROUP BY` forms groups so aggregate functions can summarize them.", "medium"),
            _q("What is a key goal of normalization in relational design?", "Reducing avoidable duplication and update anomalies.", ["Making every query use a full table scan.", "Storing every attribute in a single large table.", "Eliminating all foreign keys."], "Normalization structures relations to reduce redundancy and modification anomalies.", "medium"),
            _q("What does the atomicity property of ACID mean?", "A transaction's changes all occur or none do.", ["Committed data is always encrypted.", "Transactions never run concurrently.", "Every query returns rows in sorted order."], "Atomic transactions are treated as indivisible units of work.", "medium"),
            _q("What is a common effect of adding an index?", "Faster lookups for suitable queries, with extra storage and write cost.", ["Every query becomes faster with no trade-off.", "The table is automatically normalized.", "Duplicate values are removed from the indexed column."], "Indexes can speed reads but consume space and need maintenance on writes.", "medium"),
            _q("What is the purpose of `COMMIT`?", "Making the current transaction's changes persistent.", ["Undoing the current transaction.", "Starting a database server.", "Creating a new table."], "`COMMIT` ends a transaction by saving its changes.", "easy"),
            _q("Which predicate correctly tests whether a column is NULL?", "`column_name IS NULL`", ["`column_name = NULL`", "`column_name == NULL`", "`column_name EQUALS NULL`"], "SQL uses `IS NULL`; comparisons with NULL using `=` evaluate to unknown.", "hard"),
        ],
    },
    {
        "slug": "operating-systems",
        "title": "Operating Systems",
        "category": "Operating Systems",
        "cards": [
            _q("What is a process?", "A program in execution with managed state and resources.", ["A file stored on disk that has never run.", "A physical CPU core.", "A database transaction."], "An operating system tracks an executing program as a process.", "easy"),
            _q("What is a thread?", "A schedulable execution sequence within a process.", ["A separate physical memory chip.", "A file permissions record.", "A network routing table."], "Threads in a process commonly share its address space and resources.", "easy"),
            _q("What does a context switch involve?", "Saving one task's execution state and restoring another's.", ["Moving a file between directories.", "Changing a process's source code.", "Encrypting a page of memory."], "The scheduler switches execution by preserving and restoring CPU state.", "medium"),
            _q("What is virtual memory?", "An abstraction that gives processes address spaces mapped to physical memory.", ["A technique that makes disk storage as fast as RAM.", "A memory chip used only for graphics.", "A backup copy of every application."], "Virtual memory provides address translation and isolation, sometimes using storage as backing.", "medium"),
            _q("What is a page fault?", "An access requiring a page that is not currently mapped as needed in memory.", ["A CPU arithmetic error.", "A corrupted page in a printed book.", "A process scheduling priority."], "A page fault traps to the operating system to resolve a memory access.", "medium"),
            _q("What is deadlock?", "A state where tasks wait indefinitely for resources held by one another.", ["A process that exits normally.", "A scheduler that always selects the same priority.", "A memory page that is read-only."], "Deadlock can arise when tasks form a cycle of resource dependencies.", "medium"),
            _q("What does a CPU scheduler choose?", "Which runnable task should execute next.", ["Which files should be backed up.", "Which user may change a password.", "Which network packet should be encrypted."], "The scheduler allocates processor time among runnable tasks.", "easy"),
            _q("What is a system call?", "A controlled interface for a program to request an operating-system service.", ["A phone call made by a server.", "A hardware interrupt generated by every function.", "A database query language."], "System calls provide access to services such as files, processes, and networking.", "medium"),
            _q("What does a mutex protect?", "Exclusive access to a shared resource or critical section.", ["A process from being scheduled.", "A file from being renamed.", "A network connection from using encryption."], "A mutex allows one holder at a time to enter a protected critical section.", "medium"),
            _q("What is a race condition?", "An outcome that depends on the timing of unsynchronized operations.", ["A processor running at its maximum clock rate.", "Two processes having the same process ID.", "A program that finishes before its deadline."], "Concurrent operations can produce inconsistent results when access is not coordinated.", "medium"),
            _q("What does a page table map?", "Virtual page numbers to physical frames and related status information.", ["Files to their file extensions.", "Users to their passwords.", "CPU instructions to source code lines."], "Page tables support virtual-to-physical address translation.", "hard"),
            _q("What is the kernel?", "The privileged core of an operating system.", ["A user-installed desktop application.", "A type of source-code comment.", "A network cable connector."], "The kernel manages core resources and provides operating-system services.", "easy"),
            _q("What is one purpose of a file system?", "Organizing and locating persistent data on storage.", ["Scheduling CPU instructions.", "Encrypting every network packet.", "Assigning IP addresses to hosts."], "File systems manage names, metadata, directories, and stored file data.", "easy"),
            _q("What does preemptive scheduling allow?", "The OS to interrupt a running task and schedule another.", ["A process to disable all interrupts permanently.", "Tasks to run without a scheduler.", "Every task to execute simultaneously on one CPU."], "Preemption lets the scheduler regain control to enforce scheduling policy.", "medium"),
            _q("What does a semaphore commonly provide?", "A synchronization primitive that controls access using a counter.", ["A unique identifier for a process.", "A mapping between virtual and physical addresses.", "A method for compressing files."], "Semaphores coordinate access to limited resources and signal between tasks.", "hard"),
        ],
    },
    {
        "slug": "computer-networks",
        "title": "Computer Networking Basics",
        "category": "Networking",
        "cards": [
            _q("What is the primary purpose of DNS?", "Resolving domain names to records such as IP addresses.", ["Encrypting all files on a host.", "Assigning CPU time to processes.", "Storing CSS styles for websites."], "DNS provides a distributed naming system used to locate services.", "easy"),
            _q("What does HTTP status code 404 indicate?", "The requested resource was not found.", ["The request succeeded.", "The server encountered an internal error.", "The client must authenticate."], "A 404 response indicates that the server did not find the requested resource.", "easy"),
            _q("What does TCP provide to applications?", "A reliable, ordered byte stream between endpoints.", ["A guaranteed fixed delivery time.", "A direct mapping from domain names to IP addresses.", "Encryption by itself for every connection."], "TCP uses acknowledgments and retransmissions to provide reliable ordered delivery.", "medium"),
            _q("What is an IP address used for?", "Identifying a network interface for packet delivery.", ["Naming a programming-language variable.", "Encrypting a message without keys.", "Identifying a browser tab."], "IP addresses support addressing and routing packets across IP networks.", "easy"),
            _q("What does HTTPS add to HTTP?", "TLS-protected communication with server authentication.", ["Guaranteed zero latency.", "Automatic backups of every response.", "Unlimited bandwidth."], "HTTPS uses TLS to protect data in transit and authenticate the server endpoint.", "medium"),
            _q("What does a router do?", "Forwards packets between networks.", ["Compiles source code.", "Stores website passwords.", "Renders HTML into pixels."], "Routers use routing information to forward packets toward other networks.", "easy"),
            _q("What does a subnet mask or prefix describe?", "Which IP address bits identify the network portion.", ["The encryption algorithm for a connection.", "The physical length of a cable.", "The order of DNS records."], "A prefix length divides an IP address into network and host portions.", "medium"),
            _q("What is the role of DHCP on many networks?", "Automatically assigning network configuration to clients.", ["Translating all URLs into HTML.", "Encrypting application data.", "Filtering SQL queries."], "DHCP can provide addresses, gateways, and other configuration to clients.", "easy"),
            _q("Which transport protocol is connectionless and does not guarantee delivery?", "UDP", ["TCP", "TLS", "SSH"], "UDP sends datagrams without TCP-style connection setup or delivery guarantees.", "medium"),
            _q("What is latency?", "The time taken for data to travel or a response to arrive.", ["The maximum amount of data a link can carry per second.", "The number of IP addresses in a subnet.", "The size of a network packet."], "Latency measures delay, commonly round-trip or one-way time.", "easy"),
            _q("What does a switch commonly do on an Ethernet LAN?", "Forwards frames based on learned MAC addresses.", ["Routes packets between unrelated IP networks only.", "Resolves domain names.", "Issues TLS certificates."], "Ethernet switches learn source MAC addresses and forward frames within a LAN.", "medium"),
            _q("What is the purpose of a default gateway?", "Forwarding traffic destined for networks outside the local subnet.", ["Assigning local usernames.", "Resolving every host name locally.", "Compressing packets before transmission."], "Hosts send off-subnet traffic to a router acting as the default gateway.", "medium"),
            _q("What does bandwidth commonly describe?", "The data-carrying capacity of a link per unit time.", ["The delay before a response begins.", "The physical distance between two routers.", "The number of network protocols installed."], "Bandwidth is a rate capacity, often expressed in bits per second.", "easy"),
            _q("What is a MAC address associated with?", "A network interface at the link layer.", ["A DNS zone.", "An HTTP resource path.", "A transport-layer port."], "MAC addresses identify interfaces for local link-layer frame delivery.", "medium"),
            _q("What does TLS primarily provide for a network connection?", "Confidentiality and integrity, and authenticated peers when configured.", ["Guaranteed application correctness.", "Protection from every endpoint compromise.", "A replacement for IP routing."], "TLS protects data in transit; authentication and security depend on correct certificate validation.", "hard"),
        ],
    },
    {
        "slug": "dsa",
        "title": "Data Structures and Algorithms",
        "category": "Computer Science",
        "cards": [
            _q("What is the typical average-case lookup time in a hash table?", "O(1)", ["O(log n)", "O(n log n)", "O(n²)"], "With a suitable hash function and controlled collisions, lookup is expected constant time.", "medium"),
            _q("Which data structure follows last-in, first-out order?", "Stack", ["Queue", "Heap", "Trie"], "A stack removes the most recently added item first.", "easy"),
            _q("Which data structure follows first-in, first-out order?", "Queue", ["Stack", "Binary search tree", "Hash set"], "A queue removes items in the order they were added.", "easy"),
            _q("What condition enables binary search on an array?", "The array is sorted according to the searched ordering.", ["The array contains only unique values.", "The array has a power-of-two length.", "The array is stored as a linked list."], "Binary search discards halves based on order comparisons, requiring sorted data.", "easy"),
            _q("What is the worst-case time complexity of binary search?", "O(log n)", ["O(1)", "O(n)", "O(n log n)"], "Each comparison halves the remaining search interval.", "medium"),
            _q("What is a defining property of a binary search tree?", "Keys in each left subtree are ordered below its node and right-subtree keys above it.", ["Every node has exactly two children.", "It is always balanced.", "Its keys are stored in sorted order in an array."], "The BST ordering invariant supports search; balance is not guaranteed.", "medium"),
            _q("What does a breadth-first search use to manage its frontier?", "A queue", ["A stack only", "A min-heap in every implementation.", "A hash map sorted by key."], "BFS explores nodes level by level using a first-in, first-out queue.", "medium"),
            _q("What does depth-first search commonly use?", "A stack, explicitly or through recursion.", ["A queue exclusively.", "A sorted array of all possible paths.", "A database index."], "DFS follows a path deeply and backtracks using stack behavior.", "medium"),
            _q("What is the worst-case time complexity of merge sort?", "O(n log n)", ["O(1)", "O(log n)", "O(n²)"], "Merge sort divides input and merges sorted halves in O(n log n) time.", "medium"),
            _q("What is the worst-case time complexity of quicksort with poor pivots?", "O(n²)", ["O(1)", "O(log n)", "O(n log n)"], "Repeatedly highly unbalanced partitions can lead to quadratic work.", "hard"),
            _q("What does a min-heap guarantee at its root?", "The smallest key currently in the heap.", ["The largest key currently in the heap.", "The median key.", "The oldest inserted key in every implementation."], "A min-heap keeps each parent no greater than its children.", "medium"),
            _q("What does Big-O notation describe?", "An asymptotic upper bound on growth, up to constant factors.", ["An exact runtime in seconds.", "The memory address of an algorithm.", "A lower bound only."], "Big-O characterizes an upper growth bound as input size increases.", "medium"),
            _q("What is the typical time complexity of inserting at the head of a linked list?", "O(1)", ["O(log n)", "O(n)", "O(n log n)"], "Head insertion needs only a constant number of pointer updates.", "easy"),
            _q("What does dynamic programming commonly use?", "Stored solutions to overlapping subproblems.", ["Randomized pivots for every recursive call.", "A single globally sorted input.", "Only constant additional memory."], "Dynamic programming avoids repeated work by saving subproblem results.", "medium"),
            _q("What is a graph adjacency list?", "A representation storing each vertex with its neighboring vertices.", ["A matrix containing only vertex names.", "A sorted list of all possible paths.", "A queue of edges in traversal order."], "Adjacency lists represent sparse graphs efficiently by listing each vertex's neighbors.", "easy"),
        ],
    },
    {
        "slug": "git",
        "title": "Git Essentials",
        "category": "Developer Tools",
        "cards": [
            _q("What does `git status` report?", "The working tree and staging area state.", ["The contents of the latest commit only.", "All remote branches' file contents.", "The full history of every repository."], "`git status` summarizes staged, unstaged, and untracked changes.", "easy"),
            _q("What does `git add file` do?", "Stages the file's current content for the next commit.", ["Creates a commit immediately.", "Uploads the file to every remote.", "Deletes the file from the working tree."], "`git add` updates the index, which records proposed next-commit content.", "easy"),
            _q("What is a Git commit?", "A snapshot object recording repository content and metadata.", ["A copy of the working directory on a remote server.", "A temporary editor buffer.", "A branch name that moves with every file save."], "A commit identifies a tree snapshot plus parent and author/message metadata.", "easy"),
            _q("What does a branch name point to in Git?", "A commit reference that moves as new commits are made.", ["A separate copy of every repository object.", "A configuration file for remotes.", "A list of untracked files."], "A branch is a lightweight movable reference to a commit.", "medium"),
            _q("What does `git clone` do?", "Creates a local repository from an existing repository.", ["Combines two branches into one commit.", "Stages all modified files.", "Rewrites the remote repository's history."], "`git clone` copies repository data and checks out an initial working tree.", "easy"),
            _q("What does `git fetch` do?", "Downloads remote refs and objects without integrating them into the current branch.", ["Downloads and automatically merges every remote change.", "Deletes local branches that differ.", "Commits staged changes to the remote."], "Fetch updates remote-tracking references but does not merge into the checked-out branch.", "medium"),
            _q("What does `git pull` commonly do?", "Fetches remote changes and integrates them into the current branch.", ["Creates a new repository from the current folder.", "Only lists remote branches.", "Deletes all uncommitted changes without confirmation."], "Pull is typically a fetch followed by merge or rebase, depending on configuration.", "medium"),
            _q("What does `git merge` do?", "Integrates changes from another branch into the current branch.", ["Replaces the repository history with one file.", "Uploads a branch without downloading changes.", "Removes the index."], "Merge combines branch histories, sometimes creating a merge commit.", "easy"),
            _q("What does `git rebase` do?", "Replays commits onto a new base commit.", ["Adds a remote without changing history.", "Stages file contents for commit.", "Reverts a file to its original creation."], "Rebase recreates commits on a different parent, changing their commit identities.", "hard"),
            _q("What does `git diff --staged` show?", "Differences between the index and the current commit.", ["Differences between two remote servers.", "Only untracked files.", "The commit message of the next commit."], "The staged diff displays changes currently prepared in the index.", "medium"),
            _q("What does `.gitignore` do?", "Specifies untracked paths Git should normally ignore.", ["Removes already tracked files from repository history.", "Encrypts matching files.", "Prevents every user from viewing a branch."], "Ignore rules affect untracked files; tracked files remain tracked until explicitly removed from the index.", "medium"),
            _q("What does `git switch -c feature` do?", "Creates and switches to a new branch named `feature`.", ["Deletes the current branch.", "Commits staged changes to a branch.", "Changes the branch's upstream remote only."], "`switch -c` is the command form for creating and checking out a branch.", "easy"),
            _q("What is a merge conflict?", "A situation where Git cannot automatically reconcile overlapping changes.", ["A lost remote connection.", "A commit with no parent.", "An untracked file ignored by Git."], "Conflicts require a person to choose or combine the intended changes.", "medium"),
            _q("What does `git revert <commit>` do?", "Creates a new commit that reverses the selected commit's changes.", ["Deletes the selected commit object permanently.", "Moves the current branch to the selected commit.", "Removes every file changed by that commit."], "Revert preserves history by recording an inverse change in a new commit.", "medium"),
            _q("What does `git log --oneline` display?", "A compact commit history with one line per commit.", ["A list of ignored files.", "Only uncommitted changes.", "The current Git configuration values."], "`--oneline` abbreviates each commit's hash and message.", "easy"),
        ],
    },
    {
        "slug": "web-http-rest",
        "title": "Web, HTTP and REST",
        "category": "Web Development",
        "cards": [
            _q("What is the purpose of the HTTP `GET` method?", "Requesting a representation of a resource.", ["Replacing a resource unconditionally.", "Removing a resource.", "Submitting a partial update by definition."], "GET is intended to retrieve a representation and is defined as a safe method.", "easy"),
            _q("What does HTTP status code 201 commonly mean?", "A resource was created successfully.", ["The request is still processing.", "The resource was permanently removed.", "The server requires a proxy."], "201 Created indicates that a request resulted in a new resource.", "easy"),
            _q("What does HTTP status code 204 indicate?", "The request succeeded and the response has no content.", ["The requested page was not found.", "The client must retry with credentials.", "The server is temporarily unavailable."], "204 No Content signals success without a response representation body.", "easy"),
            _q("What does idempotency mean for an HTTP method?", "Repeating the same request has the same intended effect as making it once.", ["The request always returns identical bytes.", "The request can never change server state.", "The request must be sent only once."], "Idempotency concerns intended server effect, not necessarily identical responses.", "medium"),
            _q("Which HTTP method is commonly used for a complete replacement of a resource?", "PUT", ["GET", "TRACE", "CONNECT"], "PUT commonly creates or replaces the target resource representation.", "medium"),
            _q("Which method is commonly used for a partial resource update?", "PATCH", ["OPTIONS", "HEAD", "TRACE"], "PATCH applies partial modifications to a resource.", "medium"),
            _q("What is a REST resource commonly identified by?", "A URI.", ["A TCP sequence number.", "A browser cookie name only.", "A database password."], "REST APIs identify resources using resource identifiers such as URIs.", "easy"),
            _q("What does the `Content-Type` header describe?", "The media type of the message body.", ["The preferred server hostname.", "The user's authentication password.", "The network route to the server."], "`Content-Type` indicates how the enclosed representation should be interpreted.", "easy"),
            _q("What is the purpose of the `Accept` request header?", "Indicating response media types the client can process.", ["Specifying the request body length.", "Setting a server-side database transaction.", "Identifying a cookie's expiration time."], "`Accept` communicates acceptable response media types to the server.", "medium"),
            _q("What does a 400-level HTTP status generally indicate?", "An issue with the request or client-side conditions.", ["A successful response.", "A server-side failure in every case.", "A DNS record update."], "4xx status codes report client errors, though the specific meaning depends on the code.", "medium"),
            _q("What does a 500-level HTTP status generally indicate?", "The server failed to fulfill an apparently valid request.", ["The client has no network interface.", "The resource was created successfully.", "A redirect is always required."], "5xx status codes indicate server errors.", "easy"),
            _q("What does a stateless REST interaction mean?", "Each request contains the context needed to process it.", ["The server never stores any data.", "The client cannot use authentication.", "Every request must use a different URI."], "Statelessness means the server does not rely on stored client session context between requests.", "hard"),
            _q("Why should an API validate request bodies?", "To reject invalid input before using it in application logic.", ["To make all requests confidential automatically.", "To guarantee a database can never fail.", "To remove the need for authorization."], "Validation enforces expected shapes and constraints at the API boundary.", "easy"),
            _q("Which status code is commonly returned when authentication is required or invalid?", "401 Unauthorized", ["200 OK", "301 Moved Permanently", "304 Not Modified"], "401 indicates missing or invalid authentication credentials.", "medium"),
            _q("Which status code commonly indicates an authenticated user lacks permission?", "403 Forbidden", ["201 Created", "302 Found", "418 I'm a teapot"], "403 indicates that the server understood the request but refuses authorization.", "medium"),
        ],
    },
    {
        "slug": "cybersecurity-basics",
        "title": "Cybersecurity Basics",
        "category": "Cybersecurity",
        "cards": [
            _q("What does the confidentiality goal in the CIA triad protect?", "Information from unauthorized disclosure.", ["Information from unauthorized modification only.", "Services from any downtime.", "Data from being backed up."], "Confidentiality limits information access to authorized parties.", "easy"),
            _q("What does integrity aim to protect?", "Information from unauthorized or improper modification.", ["Information from being read by its owner.", "A system from all outages.", "Passwords from being changed."], "Integrity concerns the accuracy and trustworthiness of data.", "easy"),
            _q("What does availability mean in the CIA triad?", "Authorized users can access systems and data when needed.", ["Every user can access every record.", "Data is always stored without encryption.", "A service never needs maintenance."], "Availability supports timely and reliable access for authorized users.", "easy"),
            _q("What is multi-factor authentication?", "Using two or more distinct factor types to verify identity.", ["Using two passwords of the same type.", "Reusing one password on two websites.", "Signing in from two browser tabs."], "Factors typically include something known, possessed, or inherent.", "easy"),
            _q("What is the principle of least privilege?", "Granting only the access needed for a task and duration.", ["Giving every account administrator access.", "Sharing one account among all staff.", "Disabling permissions for all users permanently."], "Least privilege limits the damage from mistakes or compromised accounts.", "easy"),
            _q("What is a cryptographic hash designed to produce?", "A fixed-length digest from input data.", ["A reversible copy of the original plaintext.", "A secret key that decrypts all files.", "A digital certificate that proves identity by itself."], "Cryptographic hashes are one-way digests; security depends on the algorithm and use.", "medium"),
            _q("Why are unique salts used when storing password hashes?", "To make identical passwords produce different stored hash inputs.", ["To encrypt the database with a shared password.", "To let users recover plaintext passwords.", "To reduce the number of characters in each password."], "A unique salt frustrates precomputed attacks and reveals fewer password duplicates.", "medium"),
            _q("What does TLS help protect?", "Data in transit between authenticated endpoints.", ["A device from every form of malware.", "Data from an authorized user with access.", "The availability of every network service."], "TLS can provide confidentiality and integrity in transit with certificate validation.", "medium"),
            _q("Which backup practice improves resilience?", "Keeping multiple copies on different media, including an offline or separate copy.", ["Keeping one copy on the same device as the original.", "Never testing whether backups can be restored.", "Overwriting the only backup after each change."], "Separate, tested backups help recover from device failure and some destructive events.", "medium"),
            _q("What is a common warning sign of a phishing message?", "Unexpected urgency paired with a request to reveal credentials or open a link.", ["A message from a known contact with expected context.", "A routine notification verified through the official app.", "A public security advisory on an organization's website."], "Phishing often uses urgency or impersonation to prompt unsafe actions; verify through trusted channels.", "easy"),
            _q("Why should software security updates be applied promptly?", "They can fix known vulnerabilities and other defects.", ["They guarantee that a system can never be compromised.", "They replace the need for backups.", "They make authentication unnecessary."], "Patching reduces exposure to flaws for which fixes are available.", "easy"),
            _q("Where should application secrets such as API keys be kept?", "In a protected secret store or environment configuration, not source control.", ["In a public repository README.", "In client-side JavaScript bundled for every visitor.", "In a URL query parameter."], "Secrets should be access-controlled, excluded from version control, and rotated if exposed.", "easy"),
            _q("What is a key benefit of parameterized SQL queries?", "They separate query structure from user-supplied values.", ["They automatically encrypt the database file.", "They make every query run in constant time.", "They remove the need to check user permissions."], "Binding parameters prevents values from being interpreted as SQL syntax.", "medium"),
            _q("What is input validation intended to do?", "Check that input meets expected format and constraints before use.", ["Prove that every user is trustworthy.", "Replace authorization checks.", "Automatically remove all security risk."], "Validation reduces invalid input and should complement contextual output encoding and authorization.", "medium"),
            _q("What should be done first when a security incident is suspected?", "Follow the organization's incident-response process and preserve relevant evidence.", ["Delete all logs immediately.", "Post credentials in a public channel.", "Disable every backup before investigating."], "A coordinated response helps contain impact while retaining evidence for investigation.", "medium"),
        ],
    },
]


def seed_decks() -> int:
    seeded = 0
    for seed in SEED_DECKS:
        deck_id = str(uuid.uuid5(_SEED_NAMESPACE, seed["slug"]))
        cards = [
            Card(
                id=str(uuid.uuid5(_SEED_NAMESPACE, f'{seed["slug"]}:{index}')),
                deck_id=deck_id,
                type="mcq",
                **card,
            )
            for index, card in enumerate(seed["cards"], start=1)
        ]
        deck = Deck(
            id=deck_id,
            title=seed["title"],
            description=f"Curated multiple-choice practice covering {seed['category']} fundamentals.",
            category=seed["category"],
            creator="EduCards",
            cards=cards,
        )
        save_seed_deck(deck)
        seeded += len(cards)
    return seeded


if __name__ == "__main__":
    print(f"Seeded {seed_decks()} MCQs across {len(SEED_DECKS)} decks.")
