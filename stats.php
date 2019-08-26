#!/usr/bin/php
<?php

$f = fopen($argv[1], 'r');

$lines = [];
while($row = fgetcsv($f)) {
  if($row[1]) {
    $row['angle'] = abs($row[1]);
    array_push($lines, $row);
  }
}

usort($lines, function($a, $b){ return $a['angle'] < $b['angle'] ? -1 : 1; });

$hist = [];
foreach($lines as $a) {
  ++ $hist[(int)($a['angle']*20)];
}

$n = count($lines);

$j = $lines[$n-1]['angle']*20;

foreach(range(0, $j) as $i) {
  printf("%.02f°  %3d  %s\n", $i/20, $hist[$i], str_repeat('*', $hist[$i]/2));
}

echo "Samples: $n\n";
printf( "50th percentile: %.2f°\n", $lines[$n*0.5]['angle']);
printf( "90th percentile: %.2f°\n", $lines[$n*0.9]['angle']);

fclose($f);
