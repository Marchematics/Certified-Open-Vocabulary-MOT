#!/usr/bin/env Rscript

# Dense release-governance figure rebuild.
#
# Contract:
# - Backend: R only.
# - This figure replaces a standalone main-text table.
# - The goal is to merge data tables and diagnostic plots into one dense
#   Nature/NMI-style multi-panel display rather than demoting them.

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
  script_file <- "scripts/build_figure7_governance_density.R"
}
root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure7_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pal <- c(
  ink = "#282828",
  grid = "#E7E7E7",
  raw = "#9A9A9A",
  parc = "#5EA6C8",
  audit = "#99C38F",
  refusal = "#D96B5F",
  support = "#76B7B2",
  boundary = "#D6A55D",
  diagnostic = "#7C6BAA",
  null = "#F0F2F3",
  pale = "#D8EAF2"
)

theme_gov <- function(base_size = 5.4, base_family = "Arial") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.line = element_line(linewidth = 0.25, colour = pal[["ink"]]),
      axis.ticks = element_line(linewidth = 0.25, colour = pal[["ink"]]),
      axis.text = element_text(size = base_size - 0.75, colour = pal[["ink"]]),
      axis.title = element_text(size = base_size),
      legend.title = element_text(size = base_size - 0.4),
      legend.text = element_text(size = base_size - 0.8),
      legend.key.size = unit(0.16, "cm"),
      strip.background = element_rect(fill = "#F2F4F5", colour = NA),
      strip.text = element_text(size = base_size - 0.55, face = "bold"),
      plot.title = element_text(size = base_size + 0.55, face = "bold", hjust = 0),
      plot.margin = margin(2, 3, 2, 3, "pt"),
      panel.grid.major.y = element_line(linewidth = 0.18, colour = pal[["grid"]]),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank()
    )
}
theme_set(theme_gov())

save_panel <- function(plot, stem, width_mm = 91, height_mm = 45, dpi = 600) {
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
  message("wrote ", file.path("figures", "figure7_assets", "rebuild", paste0(stem, ".pdf")))
}

read_table <- function(name) read.csv(file.path(data_dir, name), stringsAsFactors = FALSE)
cap01 <- function(x) pmax(0, pmin(1, x))

# Panel a: success-domain map as a compact metric heat/bar grid.
success <- read_table("table_success_domain_features.csv")
success <- success[success$paper_status %in% c(
  "main_flagship",
  "co_primary_practical_benefit",
  "human_audit_closeout",
  "control",
  "deployment_check",
  "boundary",
  "diagnostic"
), ]
success <- success[order(success$domain, success$paper_status, success$K), ]
success$source_short <- ifelse(grepl("random", success$proposal_source), "rand",
  ifelse(grepl("audit", success$verification_mode), "audit",
    ifelse(grepl("alignn", success$proposal_source), "ALIGNN",
      ifelse(grepl("cgcnn", success$proposal_source), "CGCNN",
        ifelse(grepl("megnet", success$proposal_source), "MEGNet",
          ifelse(grepl("geometry", success$proposal_source), "geom", "main"))))))
success$row <- paste0(
  ifelse(grepl("cell", success$domain), "CTC",
    ifelse(grepl("materials", success$domain), success$source_short,
      ifelse(grepl("ecological", success$domain), "iWild",
        ifelse(grepl("earth", success$domain), "SN", "OV")))),
  " K", success$K
)
success$e_ratio <- suppressWarnings(success$max_observed_e / success$required_e)
success$e_ratio[!is.finite(success$e_ratio)] <- NA
success_long <- rbind(
  data.frame(row = success$row, metric = "release", value = cap01(success$PARC_release_size / pmax(success$K, 1)), status = success$paper_status),
  data.frame(row = success$row, metric = "PARC FTR", value = cap01(success$PARC_FTR / 0.35), status = success$paper_status),
  data.frame(row = success$row, metric = "raw FTR", value = cap01(success$raw_topK_FTR / 0.85), status = success$paper_status),
  data.frame(row = success$row, metric = "mass", value = cap01(success$evidence_mass_phi / 1.5), status = success$paper_status),
  data.frame(row = success$row, metric = "e/e_req", value = cap01(success$e_ratio / 1.5), status = success$paper_status)
)
success_long$value[is.na(success_long$value)] <- 0
success_long$row <- factor(success_long$row, levels = rev(unique(success$row)))
success_long$metric <- factor(success_long$metric, levels = c("release", "PARC FTR", "raw FTR", "mass", "e/e_req"))
p_a <- ggplot(success_long, aes(x = value, y = row, fill = status)) +
  geom_col(width = 0.70, colour = "white", linewidth = 0.10) +
  geom_vline(xintercept = 0.67, linewidth = 0.18, linetype = "dashed", colour = pal[["ink"]]) +
  facet_grid(. ~ metric) +
  scale_fill_manual(values = c(
    main_flagship = pal[["parc"]],
    co_primary_practical_benefit = pal[["support"]],
    human_audit_closeout = pal[["audit"]],
    deployment_check = pal[["boundary"]],
    control = pal[["refusal"]],
    boundary = pal[["boundary"]],
    diagnostic = pal[["diagnostic"]]
  )) +
  scale_x_continuous(limits = c(0, 1), breaks = c(0, 1), labels = c("low", "high")) +
  labs(x = "within-metric scale", y = NULL, fill = NULL, title = "Success-domain feature map") +
  theme(
    axis.text.x = element_text(size = 4.4),
    legend.position = "none"
  )
save_panel(p_a, "figure_7a_success_domain_metric_grid", 91, 51)

# Panel b: verified-positive removal load-bearing ablation.
vpr <- read_table("table_verified_positive_removal_load_bearing.csv")
vpr <- vpr[vpr$removal_mode %in% c("full_parc", "no_verified_positive_removal", "random_positive_removal"), ]
vpr$row <- vpr$target_row
vpr$row <- gsub("ctc_learned_strict_alpha010_", "CTC ", vpr$row)
vpr$row <- gsub("materials_alignn_exact_stable_alpha010_", "ALIGNN ", vpr$row)
vpr$row <- gsub("materials_cgcnn_exact_stable_alpha010_", "CGCNN ", vpr$row)
vpr$row <- gsub("materials_alignn_margin_excluded_25me[Vv]_alpha010_", "ALIGNN-m25 ", vpr$row)
vpr$row <- gsub("_", " ", vpr$row)
vpr$mode <- factor(vpr$removal_mode,
  levels = c("full_parc", "no_verified_positive_removal", "random_positive_removal"),
  labels = c("full", "no removal", "random removal")
)
vpr$row <- factor(vpr$row, levels = rev(unique(vpr$row[vpr$mode == "full"])))
p_b <- ggplot(vpr, aes(x = mean_release, y = row, fill = mode)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.66, colour = "white", linewidth = 0.10) +
  scale_fill_manual(values = c(full = pal[["parc"]], `no removal` = pal[["raw"]], `random removal` = pal[["boundary"]])) +
  labs(x = "mean release", y = NULL, fill = NULL, title = "Verified-positive removal is load-bearing") +
  theme(
    legend.position = "none"
  )
save_panel(p_b, "figure_7b_verified_positive_ablation_grid", 91, 51)

# Panel c: refusal diagnosis as max-e/mass/ILP grid.
refusal <- read_table("table_refusal_diagnosis_ilp.csv")
refusal$row <- refusal$row_id
refusal$row <- gsub("_alpha010", "", refusal$row)
refusal$row <- gsub("_", " ", refusal$row)
refusal$e_ratio <- refusal$max_e / refusal$required_e
refusal_long <- rbind(
  data.frame(row = refusal$row, metric = "max e / req.", value = cap01(refusal$e_ratio), mode = refusal$failure_mode),
  data.frame(row = refusal$row, metric = "mass Phi", value = cap01(refusal$evidence_mass_phi), mode = refusal$failure_mode),
  data.frame(row = refusal$row, metric = "ILP feasible", value = ifelse(refusal$ilp_feasible, 1, 0), mode = refusal$failure_mode)
)
refusal_long$row <- factor(refusal_long$row, levels = rev(unique(refusal$row)))
refusal_long$metric <- factor(refusal_long$metric, levels = c("max e / req.", "mass Phi", "ILP feasible"))
p_c <- ggplot(refusal_long, aes(x = value, y = row, fill = mode)) +
  geom_col(width = 0.68, colour = "white", linewidth = 0.10) +
  geom_vline(xintercept = 1, linewidth = 0.18, linetype = "dashed", colour = pal[["ink"]]) +
  facet_grid(. ~ metric) +
  scale_fill_manual(values = c(finite_resolution_cap = pal[["boundary"]], pre_graph_mass_failure = pal[["refusal"]])) +
  scale_x_continuous(limits = c(0, 1.05), breaks = c(0, 1)) +
  labs(x = NULL, y = NULL, fill = NULL, title = "Refusal diagnosis and exact-feasibility check") +
  theme(
    axis.text.x = element_text(size = 4.4),
    legend.position = "none"
  )
save_panel(p_c, "figure_7c_refusal_diagnosis_grid", 91, 43)

# Panel d: assumption diagnostics.
assump <- read_table("table_assumption_diagnostic_panel.csv")
assump <- assump[seq_len(min(nrow(assump), 10)), ]
assump$row_short <- paste0(
  ifelse(grepl("^CTC", assump$domain), "CTC",
    ifelse(grepl("materials", assump$domain, ignore.case = TRUE), "mat",
      ifelse(grepl("Space", assump$domain), "SN", "row"))),
  " ", seq_len(nrow(assump))
)
assump$e_ratio <- suppressWarnings(assump$max_observed_e / assump$required_e)
assump$nonempty_scaled <- suppressWarnings(as.numeric(assump$non_empty_seeds) / 20)
assump_long <- rbind(
  data.frame(row = assump$row_short, metric = "e/e_req", value = cap01(assump$e_ratio / 1.5), result = assump$block_sensitivity_result),
  data.frame(row = assump$row_short, metric = "mass", value = cap01(assump$best_mass_ratio / 1.5), result = assump$block_sensitivity_result),
  data.frame(row = assump$row_short, metric = "nonempty", value = cap01(assump$nonempty_scaled), result = assump$block_sensitivity_result),
  data.frame(row = assump$row_short, metric = "FTR", value = cap01(as.numeric(assump$held_out_or_human_FTR) / 0.35), result = assump$block_sensitivity_result)
)
assump_long$value[is.na(assump_long$value)] <- 0
assump_long$row <- factor(assump_long$row, levels = rev(assump$row_short))
assump_long$metric <- factor(assump_long$metric, levels = c("e/e_req", "mass", "nonempty", "FTR"))
p_d <- ggplot(assump_long, aes(x = value, y = row, fill = result)) +
  geom_col(width = 0.68, colour = "white", linewidth = 0.10) +
  facet_grid(. ~ metric) +
  scale_fill_manual(values = c(
    release_with_fine_blocks = pal[["parc"]],
    refusal_resolution_below_required_emax = pal[["boundary"]],
    certified_refusal = pal[["refusal"]]
  ), na.value = pal[["diagnostic"]]) +
  scale_x_continuous(limits = c(0, 1), breaks = c(0, 1), labels = c("low", "high")) +
  labs(x = "scaled", y = NULL, fill = NULL, title = "Assumption diagnostics") +
  theme(
    axis.text.x = element_text(size = 4.4),
    legend.position = "none"
  )
save_panel(p_d, "figure_7d_assumption_diagnostics_grid", 91, 43)

# Panel e: block-size and exchangeability diagnostics as real quantitative plots.
superu <- read_table("figure_block_size_superuniformity.csv")
superu$row <- paste0(
  ifelse(grepl("materials", superu$domain), "materials", "SpaceNet"),
  " ", superu$size_stratum
)
superu$row <- factor(superu$row, levels = rev(unique(superu$row)))
superu_long <- rbind(
  data.frame(row = superu$row, metric = "median p", value = cap01(superu$median_p_value), kind = "p"),
  data.frame(row = superu$row, metric = "KS excess", value = cap01(superu$one_sided_KS_ecdf_minus_uniform), kind = "ks"),
  data.frame(row = superu$row, metric = "blocks", value = cap01(superu$n_calibration_blocks / max(superu$n_calibration_blocks, na.rm = TRUE)), kind = "blocks"),
  data.frame(row = superu$row, metric = "false cand.", value = cap01(log10(superu$n_false_candidates + 1) / max(log10(superu$n_false_candidates + 1), na.rm = TRUE)), kind = "false")
)
superu_long$metric <- factor(superu_long$metric, levels = c("median p", "KS excess", "blocks", "false cand."))
p_e1 <- ggplot(superu_long, aes(x = value, y = row, fill = kind)) +
  geom_col(width = 0.68, colour = "white", linewidth = 0.10) +
  facet_grid(. ~ metric) +
  scale_fill_manual(values = c(p = pal[["parc"]], ks = pal[["refusal"]], blocks = pal[["raw"]], false = pal[["support"]])) +
  scale_x_continuous(limits = c(0, 1), breaks = c(0, 1), labels = c("low", "high")) +
  labs(x = "scaled", y = NULL, fill = NULL, title = "Block-size calibration diagnostics") +
  theme(axis.text.x = element_text(size = 4.2), legend.position = "none")

hetero <- read_table("table_block_size_heterogeneity_summary.csv")
hetero$domain_short <- c("materials", "CTC", "SpaceNet")[seq_len(nrow(hetero))]
hetero_long <- rbind(
  data.frame(domain = hetero$domain_short, metric = "superuniform", value = hetero$superuniformity_rows),
  data.frame(domain = hetero$domain_short, metric = "size matched", value = hetero$size_matched_rows),
  data.frame(domain = hetero$domain_short, metric = "downsampled", value = hetero$downsampled_rows)
)
hetero_long$metric <- factor(hetero_long$metric, levels = c("superuniform", "size matched", "downsampled"))
p_e2 <- ggplot(hetero_long, aes(x = domain, y = value, fill = metric)) +
  geom_col(position = position_dodge(width = 0.65), width = 0.58, colour = "white", linewidth = 0.10) +
  scale_fill_manual(values = c(superuniform = pal[["parc"]], `size matched` = pal[["support"]], downsampled = pal[["boundary"]])) +
  labs(x = NULL, y = "rows", fill = NULL, title = "Heterogeneity rerun coverage") +
  theme(axis.text.x = element_text(angle = 25, hjust = 1), legend.position = "none")

p_e <- p_e1 / p_e2 + plot_layout(heights = c(1.35, 0.75))
save_panel(p_e, "figure_7e_block_exchangeability_diagnostics", 91, 52)

# Panel f: candidate-universe scale, runtime and expectation-level validation.
runtime <- read_table("table_runtime_compute_overhead_scientific_domains.csv")
runtime$domain_short <- c("materials", "CTC", "iWildCam", "SpaceNet")[seq_len(nrow(runtime))]
runtime$universe_log10 <- log10(runtime$candidate_universe_size)
runtime$time_num <- suppressWarnings(as.numeric(runtime$calibration_and_evalue_time_sec))
runtime$time_scaled <- ifelse(is.na(runtime$time_num), 0.08, cap01(runtime$time_num / max(runtime$time_num, na.rm = TRUE)))
runtime_long <- rbind(
  data.frame(domain = runtime$domain_short, metric = "log10 candidates", value = runtime$universe_log10 / max(runtime$universe_log10), kind = "universe"),
  data.frame(domain = runtime$domain_short, metric = "table time", value = runtime$time_scaled, kind = "runtime")
)
runtime_long$domain <- factor(runtime_long$domain, levels = runtime$domain_short)
p_f <- ggplot(runtime_long, aes(x = domain, y = value, fill = kind)) +
  geom_col(position = position_dodge(width = 0.62), width = 0.55, colour = "white", linewidth = 0.10) +
  scale_fill_manual(values = c(universe = pal[["raw"]], runtime = pal[["parc"]])) +
  scale_y_continuous(limits = c(0, 1), breaks = c(0, 1), labels = c("low", "high")) +
  labs(x = NULL, y = "scaled", fill = NULL, title = "Candidate scale and table-level runtime") +
  theme(
    axis.text.x = element_text(angle = 25, hjust = 1),
    legend.position = "none"
  )

valid <- read_table("table_actual_ftr_validation_summary.csv")
valid$alpha_label <- factor(paste0("a=", valid$certified_risk_level_alpha), levels = paste0("a=", sort(unique(valid$certified_risk_level_alpha))))
valid$block_short <- ifelse(grepl("adversarial", valid$validation_block), "adversarial", "controlled")
valid_long <- rbind(
  data.frame(block = valid$block_short, alpha = valid$alpha_label, metric = "mean FTR", value = valid$mean_actual_FTR),
  data.frame(block = valid$block_short, alpha = valid$alpha_label, metric = "max FTR", value = valid$max_actual_FTR),
  data.frame(block = valid$block_short, alpha = valid$alpha_label, metric = "exceedance", value = valid$violation_rate)
)
p_f2 <- ggplot(valid_long, aes(x = alpha, y = value, fill = metric)) +
  geom_col(position = position_dodge(width = 0.65), width = 0.56, colour = "white", linewidth = 0.10) +
  facet_wrap(~block, nrow = 1) +
  scale_fill_manual(values = c(`mean FTR` = pal[["parc"]], `max FTR` = pal[["boundary"]], exceedance = pal[["refusal"]])) +
  scale_y_continuous(limits = c(0, 0.22), breaks = c(0, 0.1, 0.2)) +
  labs(x = NULL, y = NULL, fill = NULL, title = "Expectation-level validation stress") +
  theme(axis.text.x = element_text(angle = 25, hjust = 1), legend.position = "none")

p_f <- p_f / p_f2 + plot_layout(heights = c(0.85, 1.15))
save_panel(p_f, "figure_7f_runtime_validation_grid", 91, 52)

message("Done. Dense governance panel PDFs are ready for LaTeX assembly.")
