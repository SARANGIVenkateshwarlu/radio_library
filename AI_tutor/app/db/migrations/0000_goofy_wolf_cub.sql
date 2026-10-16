CREATE TABLE `phrases` (
	`id` serial AUTO_INCREMENT NOT NULL,
	`user_id` bigint unsigned NOT NULL,
	`cantonese` varchar(255) NOT NULL,
	`jyutping` varchar(512) NOT NULL,
	`english` varchar(512) NOT NULL,
	`scenario_id` varchar(64),
	`source` enum('saved','correction','bookmark') NOT NULL DEFAULT 'saved',
	`interval_days` float NOT NULL DEFAULT 0,
	`due_at` timestamp NOT NULL DEFAULT (now()),
	`ease_factor` float NOT NULL DEFAULT 2.5,
	`reps` int NOT NULL DEFAULT 0,
	`lapses` int NOT NULL DEFAULT 0,
	`last_result` varchar(16),
	`last_score` int,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `phrases_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `profiles` (
	`id` serial AUTO_INCREMENT NOT NULL,
	`device_token` varchar(64) NOT NULL,
	`name` varchar(64) NOT NULL DEFAULT 'Learner',
	`level` enum('beginner','intermediate','advanced') NOT NULL DEFAULT 'beginner',
	`daily_goal_minutes` int NOT NULL DEFAULT 10,
	`streak` int NOT NULL DEFAULT 0,
	`last_active_date` varchar(10),
	`total_speaking_seconds` int NOT NULL DEFAULT 0,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `profiles_id` PRIMARY KEY(`id`),
	CONSTRAINT `profiles_device_token_unique` UNIQUE(`device_token`)
);
--> statement-breakpoint
CREATE TABLE `sessions` (
	`id` serial AUTO_INCREMENT NOT NULL,
	`user_id` bigint unsigned NOT NULL,
	`scenario_id` varchar(64) NOT NULL,
	`mode` enum('conversation','drill','review') NOT NULL DEFAULT 'conversation',
	`started_at` timestamp NOT NULL DEFAULT (now()),
	`ended_at` timestamp,
	`duration_seconds` int NOT NULL DEFAULT 0,
	`turn_count` int NOT NULL DEFAULT 0,
	`overall_score` int,
	`summary_json` text,
	CONSTRAINT `sessions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `turns` (
	`id` serial AUTO_INCREMENT NOT NULL,
	`session_id` bigint unsigned NOT NULL,
	`user_text` text,
	`user_lang` enum('en','yue'),
	`tutor_cantonese` varchar(512),
	`tutor_jyutping` varchar(1024),
	`tutor_english` varchar(1024),
	`correction_json` text,
	`pronunciation_score` int,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `turns_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE INDEX `phrases_user_idx` ON `phrases` (`user_id`);--> statement-breakpoint
CREATE INDEX `phrases_due_idx` ON `phrases` (`user_id`,`due_at`);--> statement-breakpoint
CREATE INDEX `profiles_token_idx` ON `profiles` (`device_token`);--> statement-breakpoint
CREATE INDEX `sessions_user_idx` ON `sessions` (`user_id`);--> statement-breakpoint
CREATE INDEX `turns_session_idx` ON `turns` (`session_id`);