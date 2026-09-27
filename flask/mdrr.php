<?php





function CalculNombre($nombre):double {
    $calcul = $nombre*2;

    if($calcul >9){

        $somme = 1 + ($calcul %10);
       

    }else{
        $somme = $calcul;
    }


    return $somme 




}




for ($i=1 ; $i<=6 ;$i++){
    if ($i%2==0){
        CalculNombre($i)
    }



}


?>