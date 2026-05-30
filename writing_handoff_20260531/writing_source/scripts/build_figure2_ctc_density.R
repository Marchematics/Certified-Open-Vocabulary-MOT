#!/usr/bin/env Rscript

# Dense CTC figure rebuild.
#
# Contract:
# - Backend: R only.
# - Four large panels assembled by LaTeX.
# - Each panel is a matrix of meaningful data visualizations, not a status card.
# - Claim: CTC supplies the primary strict controlled release anchor and a
#   strong active-audit budget-efficiency signal.

required_packages <- c("ggplot2", "patchwork", "svglite")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop(
    paste0(
      "Missing required R packages: ",
      paste(missing_packages, collapse = ", "),
      ". Install with install.packages(c(",
      paste(sprintf('\"%s\"', missing_packages), collapse = ", "),
      "))."
    ),
    call. = FALSE
  )
}

library(ggplot2)
library(patchwork)

args <- commandArgs(FALSE)
script_file <- sub("^--file=", "", args[grep("^--file=", args)[1]])
if (is.na(script_file) || !nzchar(script_file)) {
  script_file <- "scripts/build_figure2_ctc_density.R"
}
root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure2_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pal <- c(
  ink = "#252525",
  grid = "#E6E6E6",
  raw = "#8F8F8F",
  parc = "#5EA6C8",
  reverse = "#476C91",
  random = "#D96B5F",
  noisy = "#D6A55D",
  support = "#76B7B2",
  faint = "#EFEFEF"
)

theme_ctc <- function(base_size = 5.45, base_family = "Arial") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.line = element_line(linewidth = 0.24, colour = pal[["ink"]]),
      axis.ticks = element_line(linewidth = 0.24, colour = pal[["ink"]]),
      axis.text = element_text(size = base_size - 0.85, colour = pal[["ink"]]),
      axis.title = element_text(size = base_size),
      axis.title.x = element_text(margin = margin(t = 2.5, unit = "pt")),
      legend.title = element_text(size = base_size - 0.45),
      legend.text = element_text(size = base_size - 0.75),
      legend.key.size = unit(0.18, "cm"),
      strip.background = element_rect(fill = "#F2F4F5", colour = NA),
      strip.text = element_text(size = base_size - 0.55, face = "bold"),
      plot.title = element_text(size = base_size + 0.7, face = "bold", hjust = 0),
      plot.margin = margin(2.5, 3.5, 7.0, 3.5, "pt"),
      panel.grid.major.y = element_line(linewidth = 0.16, colour = pal[["grid"]]),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank()
    )
}
theme_set(theme_ctc())

save_panel <- function(plot, stem, width_mm = 91, height_mm = 69, dpi = 600) {
  base <- file.path(out_dir, stem)
  w <- width_mm / 25.4
  h <- height_mm / 25.4

  svglite::svglite(paste0(base, ".svg"), width = w, height = h)
  print(plot)
  invisible(dev.off())

  grDevices::cairo_pdf(paste0(base, ".pdf"), width = w, height = h, family = "Arial")
  print(plot)
  invisible(dev.off())

  grDevices::png(paste0(base, ".png"), width = w, height = h, units = "in", res = dpi, type = "cairo")
  print(plot)
  invisible(dev.off())

  message("wrote ", file.path("figures", "figure2_assets", "rebuild", paste0(stem, ".pdf")))
}

read_table <- function(name) {
  path <- file.path(data_dir, name)
  if (!file.exists(path)) stop("Missing data file: ", path, call. = FALSE)
  read.csv(path, stringsAsFactors = FALSE)
}

metric_factor <- function(x, levels) factor(x, levels = levels)
clip <- function(x, high) pmin(x, high)

main_full <- read_table("table_ctc_learned_hybrid_main.csv")
main_full <- subset(main_full, observed_positive_strategy == "top_score")
main_small <- subset(read_table("table_ctc_learned_strict_alpha010_smallK.csv"), alpha == 0.10 & rho == 0.10)
reverse <- subset(read_table("table_ctc_learned_reverse_split.csv"), rho == 0.10)
negative <- subset(read_table("table_ctc_learned_negative_control.csv"), rho == 0.10)
lineage <- read_table("table_ctc_official_lineage_metric_summary.csv")
leak <- read_table("table_ctc_learned_leakage_audit.csv")

top_sweep <- read_table("table_ctc_topscore_partial_verification_sweep.csv")
top_sweep$policy <- "targeted"
rand_sweep <- read_table("table_ctc_random_partial_verification_sweep.csv")
rand_sweep$policy <- "random"
common_cols <- intersect(names(top_sweep), names(rand_sweep))
sweep <- rbind(top_sweep[, common_cols], rand_sweep[, common_cols])
sweep <- subset(sweep, alpha %in% c(0.10, 0.20) & M %in% c(100, 300, 500))
sweep$K <- factor(paste0("K=", sweep$M), levels = c("K=100", "K=300", "K=500"))
sweep$policy <- factor(sweep$policy, levels = c("targeted", "random"))
sweep$alpha_label <- factor(paste0("a=", sweep$alpha), levels = c("a=0.1", "a=0.2"))
sweep$audit_percent <- sweep$rho * 100
sweep$release_fraction <- sweep$released / sweep$M
sweep$mass_ratio_capped <- clip(sweep$best_mass_ratio, 1.5) / 1.5
sweep$e_ratio <- clip(sweep$max_observed_e / sweep$required_emax, 1.6) / 1.6
sweep$safe_seed <- as.numeric(sweep$released > 0 & sweep$actual_FTR <= 0.10)

# Panel a: active-audit matrix. 6 metric/alpha rows x 6 policy/K columns.
audit_long <- rbind(
  data.frame(sweep[, c("policy", "K", "alpha_label", "audit_percent", "seed")], metric = "release", value = sweep$release_fraction),
  data.frame(sweep[, c("policy", "K", "alpha_label", "audit_percent", "seed")], metric = "FTR", value = sweep$actual_FTR),
  data.frame(sweep[, c("policy", "K", "alpha_label", "audit_percent", "seed")], metric = "mass", value = sweep$mass_ratio_capped)
)
audit_long$metric <- metric_factor(audit_long$metric, c("release", "FTR", "mass"))

audit_mean <- aggregate(value ~ policy + K + alpha_label + audit_percent + metric, audit_long, mean)

p_a <- ggplot(audit_long, aes(x = audit_percent, y = value, colour = policy)) +
  geom_point(alpha = 0.22, size = 0.35, position = position_jitter(width = 0.65, height = 0), show.legend = FALSE) +
  geom_line(data = audit_mean, aes(group = policy), linewidth = 0.32, alpha = 0.95, show.legend = FALSE) +
  geom_point(data = audit_mean, size = 0.85, show.legend = FALSE) +
  geom_hline(data = data.frame(metric = factor("FTR", levels = levels(audit_long$metric)), y = 0.10),
    aes(yintercept = y), inherit.aes = FALSE, linewidth = 0.18, linetype = "dashed", colour = pal[["ink"]]) +
  facet_grid(metric + alpha_label ~ policy + K, scales = "free_y") +
  scale_colour_manual(values = c(targeted = pal[["parc"]], random = pal[["noisy"]])) +
  scale_x_continuous(breaks = c(5, 25, 50, 100), labels = c("5", "25", "50", "100")) +
  scale_y_continuous(limits = c(0, 1.05), breaks = c(0, 0.5, 1.0)) +
  labs(x = "verified-positive audit (%)", y = NULL, title = "Active-audit operating surface") +
  theme(
    strip.text = element_text(size = 4.4, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.4, face = "bold"),
    axis.text.x = element_text(size = 3.6, angle = 45, hjust = 1, vjust = 1),
    axis.text.y = element_text(size = 4.2)
  )
save_panel(p_a, "figure_2a_active_audit_density", 91, 71)

# Panel b: strict learned-source K/rho matrix. 5 metrics x 5 audit fractions.
strict <- subset(main_full, alpha == 0.10 & rho %in% c(0.05, 0.10, 0.25, 0.50, 1.00))
strict$rho_label <- factor(paste0("rho=", strict$rho * 100, "%"),
  levels = paste0("rho=", c(5, 10, 25, 50, 100), "%")
)
strict_long <- rbind(
  data.frame(strict[, c("M", "rho_label")], metric = "release", value = strict$released_mean / strict$M),
  data.frame(strict[, c("M", "rho_label")], metric = "FTR", value = strict$actual_FTR_mean),
  data.frame(strict[, c("M", "rho_label")], metric = "raw FTR", value = strict$raw_topM_actual_FTR_mean),
  data.frame(strict[, c("M", "rho_label")], metric = "mass", value = clip(strict$best_mass_ratio_mean, 1.5) / 1.5),
  data.frame(strict[, c("M", "rho_label")], metric = "e/req", value = clip(strict$max_observed_e_mean / strict$required_e, 1.6) / 1.6)
)
strict_long$metric <- metric_factor(strict_long$metric, c("release", "FTR", "raw FTR", "mass", "e/req"))

strict_long$K_label <- factor(strict_long$M, levels = c(10, 25, 50, 75, 100, 300, 500, 1000, 5000),
  labels = c("10", "25", "50", "75", "100", "300", "500", "1k", "5k")
)

p_b <- ggplot(strict_long, aes(x = K_label, y = value)) +
  geom_hline(data = data.frame(metric = factor("FTR", levels = levels(strict_long$metric)), y = 0.10),
    aes(yintercept = y), inherit.aes = FALSE, linewidth = 0.18, linetype = "dashed", colour = pal[["ink"]]) +
  geom_col(fill = pal[["parc"]], width = 0.70, colour = "white", linewidth = 0.08) +
  geom_point(size = 0.62, colour = pal[["ink"]]) +
  facet_grid(metric ~ rho_label, scales = "free_y") +
  labs(x = "requested K", y = NULL, title = "Strict learned-source release surface") +
  theme(
    strip.text = element_text(size = 4.4, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.4, face = "bold"),
    axis.text.x = element_text(size = 3.5, angle = 50, hjust = 1, vjust = 1),
    axis.text.y = element_text(size = 4.2)
  )
save_panel(p_b, "figure_2b_strict_k_sweep_density", 91, 71)

# Panel c: official lineage artifact metrics across source and K.
lineage$source <- factor(
  lineage$proposal_source,
  levels = c("ctc_learned_hybrid", "ctc_noisy_geometric_linker", "ctc_random_score_negative_control"),
  labels = c("learned", "noisy", "random")
)
lineage <- subset(lineage, !is.na(source))
lineage_long <- rbind(
  data.frame(lineage[, c("source", "K")], metric = "false edges", value = lineage$raw_false_lineage_edges_mean),
  data.frame(lineage[, c("source", "K")], metric = "prevented", value = lineage$prevented_false_lineage_edges_mean),
  data.frame(lineage[, c("source", "K")], metric = "components", value = lineage$raw_corrupted_lineage_components_mean),
  data.frame(lineage[, c("source", "K")], metric = "edit burden", value = lineage$raw_aogm_edge_edit_burden_proxy_mean),
  data.frame(lineage[, c("source", "K")], metric = "false frac.", value = lineage$raw_false_edge_fraction_mean),
  data.frame(lineage[, c("source", "K")], metric = "release", value = lineage$non_empty_seeds / lineage$seeds)
)
lineage_long$metric <- metric_factor(lineage_long$metric, c("false edges", "prevented", "components", "edit burden", "false frac.", "release"))

p_c <- ggplot(lineage_long, aes(x = K, y = value, colour = source, group = source)) +
  geom_line(linewidth = 0.34, show.legend = FALSE) +
  geom_point(size = 0.72, show.legend = FALSE) +
  facet_grid(metric ~ source, scales = "free_y") +
  scale_x_log10(breaks = c(100, 300, 500, 1000, 5000), labels = c("100", "300", "500", "1k", "5k")) +
  scale_colour_manual(values = c(learned = pal[["parc"]], noisy = pal[["noisy"]], random = pal[["random"]])) +
  labs(x = "requested K", y = NULL, title = "Official-GT lineage artifact metrics") +
  theme(
    strip.text = element_text(size = 4.4, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.2, face = "bold"),
    axis.text.x = element_text(size = 3.7, angle = 45, hjust = 1, vjust = 1),
    axis.text.y = element_text(size = 4.2)
  )
save_panel(p_c, "figure_2c_refusal_controls_density", 91, 71)

# Panel d: primary/reverse/random controls and scorer diagnostics.
primary <- subset(main_small, alpha == 0.10)
primary$source <- "primary"
reverse_strict <- subset(reverse, alpha == 0.10)
reverse_strict$source <- "reverse"
random_strict <- subset(negative, alpha == 0.10)
random_strict$source <- "random"
control <- rbind(
  data.frame(M = primary$M, source = primary$source, release = primary$released_mean / primary$M,
    FTR = primary$actual_FTR_mean, rawFTR = primary$raw_topM_actual_FTR_mean,
    mass = clip(primary$best_mass_ratio_mean, 1.5) / 1.5,
    e_ratio = clip(primary$max_observed_e_mean / primary$required_e, 1.6) / 1.6),
  data.frame(M = reverse_strict$M, source = reverse_strict$source, release = reverse_strict$released_mean / reverse_strict$M,
    FTR = reverse_strict$actual_FTR_mean, rawFTR = reverse_strict$raw_topM_actual_FTR_mean,
    mass = clip(reverse_strict$best_mass_ratio_mean, 1.5) / 1.5,
    e_ratio = clip(reverse_strict$max_observed_e_mean / reverse_strict$required_e, 1.6) / 1.6),
  data.frame(M = random_strict$M, source = random_strict$source, release = random_strict$released_mean / pmax(random_strict$M, 1),
    FTR = random_strict$actual_FTR_mean, rawFTR = random_strict$raw_topM_actual_FTR_mean,
    mass = clip(random_strict$best_mass_ratio_mean, 1.5) / 1.5,
    e_ratio = clip(random_strict$max_observed_e_mean / random_strict$required_e, 1.6) / 1.6)
)
control$source <- factor(control$source, levels = c("primary", "reverse", "random"))
control_long <- rbind(
  data.frame(control[, c("M", "source")], metric = "release", value = control$release),
  data.frame(control[, c("M", "source")], metric = "FTR", value = control$FTR),
  data.frame(control[, c("M", "source")], metric = "raw FTR", value = control$rawFTR),
  data.frame(control[, c("M", "source")], metric = "mass", value = control$mass),
  data.frame(control[, c("M", "source")], metric = "e/req", value = control$e_ratio)
)
control_long$metric <- metric_factor(control_long$metric, c("release", "FTR", "raw FTR", "mass", "e/req"))

p_d1 <- ggplot(control_long, aes(x = M, y = value, colour = source, group = source)) +
  geom_hline(data = data.frame(metric = factor("FTR", levels = levels(control_long$metric)), y = 0.10),
    aes(yintercept = y), inherit.aes = FALSE, linewidth = 0.18, linetype = "dashed", colour = pal[["ink"]]) +
  geom_line(linewidth = 0.34, show.legend = FALSE) +
  geom_point(size = 0.72, show.legend = FALSE) +
  facet_grid(metric ~ source, scales = "free_y") +
  scale_x_log10(breaks = c(10, 50, 100, 300), labels = c("10", "50", "100", "300")) +
  scale_colour_manual(values = c(primary = pal[["parc"]], reverse = pal[["reverse"]], random = pal[["random"]])) +
  labs(x = "requested K", y = NULL, title = "Split and destroyed-ranking controls") +
  theme(
    strip.text = element_text(size = 4.4, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.2, face = "bold"),
    axis.text.x = element_text(size = 3.7, angle = 45, hjust = 1, vjust = 1),
    axis.text.y = element_text(size = 4.2)
  )

leak_values <- data.frame(
  check = factor(c("primary AP", "primary AUC", "reverse AP", "reverse AUC"), levels = c("primary AP", "primary AUC", "reverse AP", "reverse AUC")),
  value = c(
    leak$eval_average_precision[leak$check_name == "primary_sequence_disjoint_split"],
    leak$eval_auc[leak$check_name == "primary_sequence_disjoint_split"],
    leak$eval_average_precision[leak$check_name == "reverse_sequence_disjoint_split"],
    leak$eval_auc[leak$check_name == "reverse_sequence_disjoint_split"]
  )
)
p_d2 <- ggplot(leak_values, aes(x = check, y = value)) +
  geom_col(fill = pal[["support"]], width = 0.62, colour = "white", linewidth = 0.12) +
  geom_point(size = 0.72, colour = pal[["ink"]]) +
  coord_cartesian(ylim = c(0.995, 1.000)) +
  labs(x = NULL, y = NULL, title = "Held-out scorer diagnostics") +
  theme(axis.text.x = element_text(size = 3.7, angle = 45, hjust = 1, vjust = 1))

p_d <- p_d1 / p_d2 + plot_layout(heights = c(1.0, 0.24))
save_panel(p_d, "figure_2d_reverse_leakage_density", 91, 71)

message("Done. Dense CTC panel PDFs are ready for LaTeX assembly.")
